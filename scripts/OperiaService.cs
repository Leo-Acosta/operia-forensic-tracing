// Compile with the Windows .NET Framework compiler; no third-party service wrapper.
using System;
using System.IO;
using System.Diagnostics;
using System.ServiceProcess;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Collections;
using System.Collections.Generic;

[DataContract] class Ready {
    [DataMember] public string state;
    [DataMember] public string generation;
    [DataMember] public int pid;
}
class OperiaService : ServiceBase {
    readonly string root;
    Process child;
    IntPtr job;
    string generation;
    volatile bool stopping;
    [StructLayout(LayoutKind.Sequential)] struct BasicLimit {
        public long ProcessTime, JobTime; public uint Flags;
        public UIntPtr MinWorking, MaxWorking; public uint Active;
        public UIntPtr Affinity; public uint Priority, Scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters { public ulong a,b,c,d,e,f; }
    [StructLayout(LayoutKind.Sequential)] struct JobLimit {
        public BasicLimit Basic; public IoCounters Io;
        public UIntPtr ProcessMemory,JobMemory,PeakProcessMemory,PeakJobMemory;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct Startup {
        public int cb; public string reserved, desktop, title;
        public int x,y,cx,cy,charsX,charsY,fill,flags;
        public short show, reservedSize; public IntPtr reservedBytes,input,output,error;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo { public IntPtr process,thread; public uint pid,tid; }
    [DllImport("kernel32",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr sa,string name);
    [DllImport("kernel32",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr j,int kind,ref JobLimit value,uint length);
    [DllImport("kernel32",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
    [DllImport("kernel32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder command,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref Startup start,out ProcessInfo info);
    [DllImport("kernel32",SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32")] static extern bool TerminateProcess(IntPtr p,uint code);
    [DllImport("kernel32")] static extern bool CloseHandle(IntPtr p);
    [DllImport("kernel32")] static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32")] static extern IntPtr LocalFree(IntPtr p);
    [StructLayout(LayoutKind.Sequential)] struct MandatoryLabel {public IntPtr Sid; public uint Attributes;}
    [DllImport("advapi32",SetLastError=true)] static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSidToSidW(string sid,out IntPtr pointer);
    [DllImport("advapi32")] static extern uint GetLengthSid(IntPtr sid);
    [DllImport("advapi32",SetLastError=true)] static extern bool SetTokenInformation(IntPtr token,int kind,ref MandatoryLabel label,uint length);
    static void LowerIntegrity() {
        IntPtr token=IntPtr.Zero,sid=IntPtr.Zero;
        try {
            Check(OpenProcessToken(GetCurrentProcess(),0x88,out token));
            Check(ConvertStringSidToSidW("S-1-16-8192",out sid));
            var label=new MandatoryLabel {Sid=sid,Attributes=0x20};
            Check(SetTokenInformation(token,25,ref label,(uint)Marshal.SizeOf(typeof(MandatoryLabel))+GetLengthSid(sid)));
        } finally {if(token!=IntPtr.Zero) CloseHandle(token); if(sid!=IntPtr.Zero) LocalFree(sid);}
    }
    static void Check(bool ok) { if(!ok) throw new InvalidOperationException("service_native_operation_failed_"+Marshal.GetLastWin32Error()); }
    static void NoLinks(string path) {
        for(var d=new DirectoryInfo(path); d!=null; d=d.Parent)
            if((d.Attributes & FileAttributes.ReparsePoint)!=0) throw new InvalidOperationException("service_link_rejected");
    }
    public OperiaService(string path,string name) {
        root=Path.GetFullPath(path); NoLinks(root); ServiceName=name;
        CanStop=true; CanShutdown=true; AutoLog=false;
    }
    protected override void OnStart(string[] args) {
        RequestAdditionalTime(120000); stopping=false;
        LowerIntegrity(); // SCM logon can have a high mandatory label; never retain it.
        string release=File.ReadAllText(Path.Combine(root,"config","active-release.txt")).Trim();
        if(!System.Text.RegularExpressions.Regex.IsMatch(release,"\\A[a-f0-9]{24}\\z")) throw new InvalidOperationException("service_release_invalid");
        string baseDir=Path.Combine(root,"releases",release); NoLinks(baseDir);
        string exe=Path.Combine(baseDir,"runtime","python.exe");
        generation=Guid.NewGuid().ToString("N");
        var vars=new SortedDictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        foreach(string key in new[]{"SystemRoot","WINDIR"}) {
            string value=Environment.GetEnvironmentVariable(key); if(value!=null) vars[key]=value;
        }
        vars["USERPROFILE"]=Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        vars["APPDATA"]=Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        vars["LOCALAPPDATA"]=Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        if(String.IsNullOrEmpty(vars["USERPROFILE"]) || String.IsNullOrEmpty(vars["LOCALAPPDATA"])) throw new InvalidOperationException("service_profile_unavailable");
        vars["PATH"]=Path.Combine(baseDir,"runtime")+";"+Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"System32");
        vars["TEMP"]=vars["TMP"]=Path.Combine(root,"data","temp");
        vars["OPERIA_SERVICE_ROOT"]=root; vars["OPERIA_SERVICE_GENERATION"]=generation;
        var block=new StringBuilder(); foreach(var pair in vars) block.Append(pair.Key).Append('=').Append(pair.Value).Append('\0'); block.Append('\0');
        IntPtr env=Marshal.StringToHGlobalUni(block.ToString());
        ProcessInfo info=new ProcessInfo();
        try {
            job=CreateJobObject(IntPtr.Zero,null); Check(job!=IntPtr.Zero);
            var limit=new JobLimit(); limit.Basic.Flags=0x2000; // KILL_ON_JOB_CLOSE
            Check(SetInformationJobObject(job,9,ref limit,(uint)Marshal.SizeOf(typeof(JobLimit))));
            var startup=new Startup(); startup.cb=Marshal.SizeOf(typeof(Startup));
            Check(CreateProcess(exe,new StringBuilder("\""+exe+"\" -B -m scripts.windows_service_supervisor"),IntPtr.Zero,IntPtr.Zero,false,0x08000404,env,Path.Combine(baseDir,"code"),ref startup,out info));
            // Assign while suspended: every descendant belongs to this kill-on-close job.
            Check(AssignProcessToJobObject(job,info.process));
            child=Process.GetProcessById((int)info.pid);
            Check(ResumeThread(info.thread)!=0xffffffff);
            DateTime until=DateTime.UtcNow.AddSeconds(105); bool ready=false;
            while(DateTime.UtcNow<until && !child.HasExited) {
                try {
                    using(var input=File.OpenRead(Path.Combine(root,"data","logs","service-state.json"))) {
                        var value=(Ready)new DataContractJsonSerializer(typeof(Ready)).ReadObject(input);
                        ready=value.state=="ready" && value.generation==generation && value.pid==child.Id;
                    }
                } catch(IOException) {} catch(SerializationException) {}
                if(ready) break; System.Threading.Thread.Sleep(200);
            }
            if(!ready) throw new InvalidOperationException("service_readiness_failed");
            child.EnableRaisingEvents=true;
            child.Exited+=(s,e)=>{if(!stopping) Environment.Exit(17);};
            if(child.HasExited) Environment.Exit(17);
        } catch { if(info.process!=IntPtr.Zero) TerminateProcess(info.process,17); CloseJob(); throw; }
        finally { Marshal.FreeHGlobal(env); if(info.thread!=IntPtr.Zero) CloseHandle(info.thread); if(info.process!=IntPtr.Zero) CloseHandle(info.process); }
    }
    void CloseJob() { if(job!=IntPtr.Zero) { CloseHandle(job); job=IntPtr.Zero; } }
    protected override void OnStop() {
        StopChildren(true);
    }
    void StopChildren(bool normalStop) {
        stopping=true; if(normalStop) RequestAdditionalTime(90000);
        try {
            File.WriteAllText(Path.Combine(root,"data","control","stop-"+generation),"");
            if(child!=null) child.WaitForExit(normalStop?75000:10000);
        } finally { CloseJob(); if(child!=null) {child.Dispose(); child=null;} }
    }
    protected override void OnShutdown() { StopChildren(false); }
    static void Main(string[] args) {
        if(args.Length!=2) Environment.Exit(2);
        ServiceBase.Run(new OperiaService(args[0],args[1]));
    }
}
