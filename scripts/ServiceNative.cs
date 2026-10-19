// Administrative interop. Passwords remain SecureString/unmanaged buffers, never argv.
using System;
using System.Security;
using System.Runtime.InteropServices;
public static class OperiaServiceNative {
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct Credential {
        public uint Flags,Type; public string Target,Comment; public long Written;
        public uint Size; public IntPtr Blob; public uint Persist,Count;
        public IntPtr Attributes; public string Alias,User;
    }
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CredWriteW(ref Credential value,uint flags);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CredReadW(string target,uint type,uint flags,out IntPtr value);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CredDeleteW(string target,uint type,uint flags);
    [DllImport("advapi32")] static extern void CredFree(IntPtr value);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr OpenSCManagerW(string machine,string database,uint access);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateServiceW(IntPtr scm,string name,string display,uint access,uint type,uint start,uint error,string binary,string group,IntPtr tag,string dependencies,string account,IntPtr password);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr OpenServiceW(IntPtr scm,string name,uint access);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ChangeServiceConfigW(IntPtr svc,uint type,uint start,uint error,string binary,string group,IntPtr tag,string dependencies,string account,IntPtr password,string display);
    [DllImport("advapi32")] static extern bool CloseServiceHandle(IntPtr handle);
    [DllImport("advapi32",SetLastError=true)] static extern bool ChangeServiceConfig2W(IntPtr svc,uint level,IntPtr info);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text,uint revision,out IntPtr sd,out uint size);
    [DllImport("advapi32",SetLastError=true)] static extern bool SetServiceObjectSecurity(IntPtr svc,uint info,IntPtr sd);
    [DllImport("kernel32")] static extern IntPtr LocalFree(IntPtr memory);
    [StructLayout(LayoutKind.Sequential)] struct SecBuffer {public uint Size,Type; public IntPtr Data;}
    [StructLayout(LayoutKind.Sequential)] struct SecBufferDesc {public uint Version,Count; public IntPtr Buffers;}
    [DllImport("secur32",CharSet=CharSet.Unicode,ExactSpelling=true)] static extern uint ChangeAccountPasswordW(string package,string domain,string user,IntPtr oldPassword,IntPtr newPassword,byte impersonating,uint reserved,ref SecBufferDesc output);
    [DllImport("secur32")] static extern uint FreeContextBuffer(IntPtr buffer);
    [DllImport("netapi32",CharSet=CharSet.Unicode)] static extern uint NetUserChangePassword(string domain,string user,IntPtr oldPassword,IntPtr newPassword);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool LogonUserW(string user,string domain,IntPtr password,int type,int provider,out IntPtr token);
    [DllImport("kernel32")] static extern bool CloseHandle(IntPtr token);
    [DllImport("advapi32",SetLastError=true)] static extern bool ImpersonateLoggedOnUser(IntPtr token);
    [DllImport("advapi32",SetLastError=true)] static extern bool RevertToSelf();
    [StructLayout(LayoutKind.Sequential)] struct SecurityAttributes {public int Length; public IntPtr Descriptor; public int Inherit;}
    [DllImport("kernel32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateDirectoryW(string path,ref SecurityAttributes attributes);
    [StructLayout(LayoutKind.Sequential)] struct LsaObject { public uint Length; public IntPtr Root,Name; public uint Attributes; public IntPtr Security,Qos; }
    [StructLayout(LayoutKind.Sequential)] struct LsaString { public ushort Length,MaximumLength; public IntPtr Buffer; }
    [DllImport("advapi32")] static extern uint LsaOpenPolicy(IntPtr system,ref LsaObject attr,uint access,out IntPtr policy);
    [DllImport("advapi32")] static extern uint LsaAddAccountRights(IntPtr policy,IntPtr sid,[In] LsaString[] rights,uint count);
    [DllImport("advapi32")] static extern uint LsaClose(IntPtr policy);
    [DllImport("advapi32")] static extern uint LsaNtStatusToWinError(uint status);
    [DllImport("advapi32",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool ConvertStringSidToSidW(string sid,out IntPtr pointer);
    [StructLayout(LayoutKind.Sequential)] struct Action { public uint Type,Delay; }
    [StructLayout(LayoutKind.Sequential)] struct Failure { public uint Reset; public IntPtr Reboot,Command; public uint Count; public IntPtr Actions; }
    static void Check(bool value) { if(!value) throw new InvalidOperationException("service_native_error_"+Marshal.GetLastWin32Error()); }
    public static void PrivateDirectory(string path) {
        IntPtr descriptor; uint size;
        Check(ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)",1,out descriptor,out size));
        try {var attr=new SecurityAttributes {Length=Marshal.SizeOf(typeof(SecurityAttributes)),Descriptor=descriptor}; Check(CreateDirectoryW(path,ref attr));}
        finally {LocalFree(descriptor);}
    }
    public static SecureString NewPassword() {
        byte[] bytes=new byte[48]; using(var rng=System.Security.Cryptography.RandomNumberGenerator.Create()) rng.GetBytes(bytes);
        var result=new SecureString(); foreach(char c in "Aa1!") result.AppendChar(c);
        const string alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#%+-_";
        foreach(byte b in bytes) result.AppendChar(alphabet[b%alphabet.Length]); Array.Clear(bytes,0,bytes.Length);
        result.MakeReadOnly(); return result;
    }
    public static void Store(string target,string user,SecureString password) {
        IntPtr blob=Marshal.SecureStringToGlobalAllocUnicode(password);
        try { var value=new Credential {Type=1,Target=target,User=user,Persist=2,Size=(uint)password.Length*2,Blob=blob}; Check(CredWriteW(ref value,0)); }
        finally { Marshal.ZeroFreeGlobalAllocUnicode(blob); }
    }
    public static SecureString Read(string target) {
        IntPtr pointer;
        if(!CredReadW(target,1,0,out pointer)) {
            if(Marshal.GetLastWin32Error()==1168) return null;
            Check(false);
        }
        try {
            var value=(Credential)Marshal.PtrToStructure(pointer,typeof(Credential));
            if(value.Size>1024 || value.Size%2!=0) throw new InvalidOperationException("service_credential_invalid");
            var secret=new SecureString(); for(int i=0;i<value.Size;i+=2) secret.AppendChar((char)Marshal.ReadInt16(value.Blob,i));
            for(int i=0;i<value.Size;i++) Marshal.WriteByte(value.Blob,i,0);
            secret.MakeReadOnly(); return secret;
        } finally { CredFree(pointer); }
    }
    public static void Delete(string target) { if(!CredDeleteW(target,1,0) && Marshal.GetLastWin32Error()!=1168) Check(false); }
    public static bool Valid(string user,SecureString password) {
        IntPtr raw=Marshal.SecureStringToGlobalAllocUnicode(password),token;
        try { if(!LogonUserW(user,".",raw,5,0,out token)) return false; CloseHandle(token); return true; }
        finally { Marshal.ZeroFreeGlobalAllocUnicode(raw); }
    }
    public static void ChangePassword(string user,SecureString oldPassword,SecureString newPassword) {
        IntPtr oldRaw=Marshal.SecureStringToGlobalAllocUnicode(oldPassword),newRaw=Marshal.SecureStringToGlobalAllocUnicode(newPassword);
        // Regular changes use compatible lengths and the local NetAPI path.
        // SSPI is only a bridge for an existing long credential; neither path
        // performs an administrative password reset. Readiness must prove DPAPI.
        IntPtr buffer=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(SecBuffer)));
        Marshal.StructureToPtr(new SecBuffer {Type=15},buffer,false);
        var output=new SecBufferDesc {Count=1,Buffers=buffer};
        try {
            uint status;
            if(oldPassword.Length<=63 && newPassword.Length<=63) {
                IntPtr token;
                Check(LogonUserW(user,".",oldRaw,5,0,out token));
                try {
                    Check(ImpersonateLoggedOnUser(token));
                    try {status=NetUserChangePassword(Environment.MachineName,user,oldRaw,newRaw);}
                    finally {if(!RevertToSelf()) Environment.FailFast("service_revert_failed");}
                } finally {CloseHandle(token);}
                if(status!=0) throw new InvalidOperationException("service_password_change_failed_"+status);
                return;
            }
            status=ChangeAccountPasswordW("NTLM",Environment.MachineName,user,oldRaw,newRaw,0,0,ref output);
            if(status!=0) throw new InvalidOperationException("service_password_change_failed_sspi_"+status.ToString("x8"));
        } finally {
            var response=(SecBuffer)Marshal.PtrToStructure(buffer,typeof(SecBuffer));
            if(response.Data!=IntPtr.Zero) FreeContextBuffer(response.Data);
            Marshal.FreeHGlobal(buffer);
            Marshal.ZeroFreeGlobalAllocUnicode(oldRaw); Marshal.ZeroFreeGlobalAllocUnicode(newRaw);
        }
    }
    public static void Rights(string sid) {
        IntPtr pointer,policy=IntPtr.Zero; Check(ConvertStringSidToSidW(sid,out pointer));
        try {
            var attr=new LsaObject(); attr.Length=(uint)Marshal.SizeOf(typeof(LsaObject));
            uint status=LsaOpenPolicy(IntPtr.Zero,ref attr,0x810,out policy);
            if(status!=0) throw new InvalidOperationException("service_lsa_open_"+LsaNtStatusToWinError(status));
            foreach(string name in new[]{"SeServiceLogonRight","SeDenyInteractiveLogonRight","SeDenyRemoteInteractiveLogonRight","SeDenyNetworkLogonRight"}) {
                IntPtr raw=Marshal.StringToHGlobalUni(name);
                try { var right=new LsaString {Length=(ushort)(name.Length*2),MaximumLength=(ushort)((name.Length+1)*2),Buffer=raw};
                    status=LsaAddAccountRights(policy,pointer,new[]{right},1);
                    if(status!=0) throw new InvalidOperationException("service_lsa_right_"+LsaNtStatusToWinError(status));
                } finally { Marshal.FreeHGlobal(raw); }
            }
        } finally { if(policy!=IntPtr.Zero) LsaClose(policy); LocalFree(pointer); }
    }
    public static void SetRecoveryReset(string name,uint seconds) {
        if(seconds!=0 && seconds!=86400) throw new ArgumentOutOfRangeException("seconds");
        IntPtr scm=OpenSCManagerW(null,null,1);Check(scm!=IntPtr.Zero);
        IntPtr svc=IntPtr.Zero,actions=IntPtr.Zero,failure=IntPtr.Zero;
        try {
            // Configuring SC_ACTION_RESTART also requires SERVICE_START.
            svc=OpenServiceW(scm,name,0x12);Check(svc!=IntPtr.Zero);
            int size=Marshal.SizeOf(typeof(Action));actions=Marshal.AllocHGlobal(size*4);
            for(int i=0;i<4;i++) Marshal.StructureToPtr(new Action {Type=i<3?1u:0u,Delay=(uint)(i==0?5000:i==1?15000:30000)},IntPtr.Add(actions,i*size),false);
            failure=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Failure)));
            Marshal.StructureToPtr(new Failure {Reset=seconds,Count=4,Actions=actions},failure,false);
            Check(ChangeServiceConfig2W(svc,2,failure));
        } finally {
            if(failure!=IntPtr.Zero) Marshal.FreeHGlobal(failure);
            if(actions!=IntPtr.Zero) Marshal.FreeHGlobal(actions);
            if(svc!=IntPtr.Zero) CloseServiceHandle(svc);CloseServiceHandle(scm);
        }
    }
    public static void Configure(string name,string binary,string user,SecureString password,bool create) {
        IntPtr scm=OpenSCManagerW(null,null,3); Check(scm!=IntPtr.Zero);
        IntPtr raw=Marshal.SecureStringToGlobalAllocUnicode(password),svc=IntPtr.Zero;
        try {
            svc=create ? CreateServiceW(scm,name,"OPERIA controlled validation",0xf01ff,0x10,3,1,binary,null,IntPtr.Zero,null,".\\"+user,raw) : OpenServiceW(scm,name,0xf01ff);
            Check(svc!=IntPtr.Zero);
            if(!create) Check(ChangeServiceConfigW(svc,0xffffffff,3,0xffffffff,null,null,IntPtr.Zero,null,".\\"+user,raw,null));
            int actionSize=Marshal.SizeOf(typeof(Action)); IntPtr actions=Marshal.AllocHGlobal(actionSize*4),failure=IntPtr.Zero,flag=IntPtr.Zero,sd=IntPtr.Zero;
            try {
                for(int i=0;i<4;i++) Marshal.StructureToPtr(new Action {Type=i<3?1u:0u,Delay=(uint)(i==0?5000:i==1?15000:30000)},IntPtr.Add(actions,i*actionSize),false);
                failure=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Failure)));
                Marshal.StructureToPtr(new Failure {Reset=86400,Count=4,Actions=actions},failure,false);
                Check(ChangeServiceConfig2W(svc,2,failure));
                flag=Marshal.AllocHGlobal(4); Marshal.WriteInt32(flag,1); Check(ChangeServiceConfig2W(svc,4,flag));
                IntPtr privileges=Marshal.StringToHGlobalUni("SeChangeNotifyPrivilege\0\0"),required=Marshal.AllocHGlobal(IntPtr.Size);
                try {Marshal.WriteIntPtr(required,privileges); Check(ChangeServiceConfig2W(svc,6,required));}
                finally {Marshal.FreeHGlobal(privileges); Marshal.FreeHGlobal(required);}
                uint size; Check(ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;CCLCSWLOCRRC;;;AU)",1,out sd,out size));
                Check(SetServiceObjectSecurity(svc,4,sd));
            } finally { Marshal.FreeHGlobal(actions); if(failure!=IntPtr.Zero) Marshal.FreeHGlobal(failure); if(flag!=IntPtr.Zero) Marshal.FreeHGlobal(flag); if(sd!=IntPtr.Zero) LocalFree(sd); }
        } finally { Marshal.ZeroFreeGlobalAllocUnicode(raw); if(svc!=IntPtr.Zero) CloseServiceHandle(svc); CloseServiceHandle(scm); }
    }
}
