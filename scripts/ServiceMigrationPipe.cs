// One local connection, authenticated service client, no secret on disk/argv/env.
using System;
using System.Security;
using System.Security.Principal;
using System.Runtime.InteropServices;
using System.Threading;
using System.Text;
using System.Security.Cryptography;
public sealed class OperiaMigrationPipe : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct Attributes {public int Size;public IntPtr Descriptor;public int Inherit;}
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string value,uint revision,out IntPtr sd,out uint size);
    [DllImport("kernel32",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateNamedPipeW(string name,uint mode,uint flags,uint instances,uint output,uint input,uint timeout,ref Attributes sa);
    [DllImport("kernel32",SetLastError=true)] static extern bool ConnectNamedPipe(IntPtr pipe,IntPtr overlapped);
    [DllImport("kernel32",SetLastError=true)] static extern bool GetNamedPipeClientProcessId(IntPtr pipe,out uint pid);
    [DllImport("kernel32",SetLastError=true)] static extern bool ReadFile(IntPtr file,byte[] bytes,uint size,out uint read,IntPtr overlapped);
    [DllImport("kernel32",SetLastError=true)] static extern bool WriteFile(IntPtr file,byte[] bytes,uint size,out uint written,IntPtr overlapped);
    [DllImport("kernel32",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
    [DllImport("advapi32",SetLastError=true)] static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
    [DllImport("kernel32")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32")] static extern IntPtr LocalFree(IntPtr pointer);
    [DllImport("kernel32")] static extern bool CancelIoEx(IntPtr file,IntPtr overlapped);
    IntPtr handle;
    SecureString secret;
    readonly string sid;
    Thread thread;
    public volatile bool Completed;
    public string Error {get;private set;}
    static void Check(bool value) {if(!value) throw new InvalidOperationException("migration_pipe_native_"+Marshal.GetLastWin32Error());}
    public OperiaMigrationPipe(string root,string accountSid,SecureString password) {
        new SecurityIdentifier(accountSid); sid=accountSid; secret=password.Copy();
        string hash;using(var sha=SHA256.Create()) hash=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(root.TrimEnd('\\').ToLowerInvariant()))).Replace("-", "").ToLowerInvariant();
        IntPtr sd;uint size;
        Check(ConvertStringSecurityDescriptorToSecurityDescriptorW("O:BAG:BAD:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;"+sid+")",1,out sd,out size));
        try {
            var attrs=new Attributes {Size=Marshal.SizeOf(typeof(Attributes)),Descriptor=sd};
            // FIRST_PIPE_INSTANCE + local-only byte stream, one instance.
            handle=CreateNamedPipeW(@"\\.\pipe\OperiaDpapi-"+hash,0x80003,8,1,4096,128,1000,ref attrs);
            if(handle==new IntPtr(-1)) {handle=IntPtr.Zero;Check(false);}
        } catch {secret.Dispose();throw;} finally {LocalFree(sd);}
        thread=new Thread(Serve);thread.IsBackground=true;thread.Start();
    }
    void Send(byte[] bytes) {uint written;Check(WriteFile(handle,bytes,(uint)bytes.Length,out written,IntPtr.Zero));if(written!=bytes.Length) throw new InvalidOperationException("migration_pipe_short_write");}
    void Serve() {
        byte[] payload=null;IntPtr raw=IntPtr.Zero;
        try {
            if(!ConnectNamedPipe(handle,IntPtr.Zero) && Marshal.GetLastWin32Error()!=535) Check(false);
            byte[] hello=new byte[64];uint read;Check(ReadFile(handle,hello,64,out read,IntPtr.Zero));
            if(Encoding.ASCII.GetString(hello,0,(int)read)!="OPERIA-DPAPI/1") throw new InvalidOperationException("migration_pipe_handshake_rejected");
            uint pid;Check(GetNamedPipeClientProcessId(handle,out pid));
            IntPtr process=OpenProcess(0x1000,false,pid),token=IntPtr.Zero;Check(process!=IntPtr.Zero);
            try {Check(OpenProcessToken(process,8,out token));using(var identity=new WindowsIdentity(token)) if(identity.User.Value!=sid) throw new InvalidOperationException("migration_pipe_client_sid_rejected");}
            finally {if(token!=IntPtr.Zero) CloseHandle(token);CloseHandle(process);}
            raw=Marshal.SecureStringToGlobalAllocUnicode(secret);
            payload=new byte[secret.Length*2];Marshal.Copy(raw,payload,0,payload.Length);
            Send(BitConverter.GetBytes(payload.Length));Send(payload);Completed=true;
        } catch {Error="service_migration_pipe_failed";}
        finally {if(payload!=null) Array.Clear(payload,0,payload.Length);if(raw!=IntPtr.Zero) Marshal.ZeroFreeGlobalAllocUnicode(raw);secret.Dispose();}
    }
    public void Dispose() {
        if(handle!=IntPtr.Zero) {CancelIoEx(handle,IntPtr.Zero);CloseHandle(handle);handle=IntPtr.Zero;}
        if(thread!=null) thread.Join(1500);
    }
}
