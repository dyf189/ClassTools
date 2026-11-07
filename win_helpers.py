# -*- coding: utf-8 -*-
"""Windows 系统辅助：隐藏控制台/任务栏、电源操作（不调用 shutdown.exe）"""
import sys
import ctypes
import subprocess


# ---------- 隐藏控制台窗口 ----------
def hide_console():
    """隐藏控制台窗口"""
    try:
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window != 0:
            # 隐藏控制台
            ctypes.windll.user32.ShowWindow(console_window, 0)  # 0 = SW_HIDE
            print("控制台已隐藏")
    except Exception:
        pass  # 静默处理，不影响程序运行


# ---------- 隐藏任务栏图标 ----------
def hide_from_taskbar(window):
    """兼容不同Python/Windows版本的隐藏任务栏方法"""
    if sys.platform != 'win32':
        return

    try:
        hwnd = int(window.winId())

        # 尝试多种API函数名
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000

        user32 = ctypes.windll.user32

        set_func = None
        get_func = None

        for func_name in ['SetWindowLongPtrW', 'SetWindowLongW', 'SetWindowLongA']:
            if hasattr(user32, func_name):
                set_func = getattr(user32, func_name)
                break

        for func_name in ['GetWindowLongPtrW', 'GetWindowLongW', 'GetWindowLongA']:
            if hasattr(user32, func_name):
                get_func = getattr(user32, func_name)
                break

        if set_func and get_func:
            # 获取当前样式
            ex_style = get_func(hwnd, GWL_EXSTYLE)
            # 修改样式
            new_ex_style = (ex_style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
            # 设置新样式
            set_func(hwnd, GWL_EXSTYLE, new_ex_style)

            # 刷新窗口
            user32.ShowWindow(hwnd, 0)
            window.show()
            return True

    except Exception as e:
        print(f"隐藏任务栏失败（将使用普通模式）: {e}")
        return False


# ---------- 取消旧版 shutdown.exe 计划 ----------
def abort_legacy_shutdown():
    """取消旧版本用 shutdown.exe 设置的待执行关机（如有），避免双保险冲突"""
    try:
        subprocess.run("shutdown /a", shell=True, capture_output=True)
    except Exception:
        pass


# ---------- 电源操作（不走 shutdown.exe，避免“此计算机将在xx分钟后注销”提示） ----------
EWX_SHUTDOWN = 0x00000001
EWX_REBOOT = 0x00000002
EWX_POWEROFF = 0x00000008
EWX_FORCEIFHUNG = 0x00000010


class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]


class _LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", _LUID), ("Attributes", ctypes.c_ulong)]


class _TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", ctypes.c_ulong),
                ("Privileges", _LUID_AND_ATTRIBUTES * 1)]


def _enable_shutdown_privilege():
    """为当前进程启用 SeShutdownPrivilege（关机 API 需要该权限）"""
    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32
    TOKEN_ADJUST_PRIVILEGES = 0x20
    TOKEN_QUERY = 0x8
    SE_PRIVILEGE_ENABLED = 0x2

    htoken = ctypes.c_void_p()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(htoken)):
        return False
    try:
        luid = _TOKEN_PRIVILEGES._LUID()
        if not advapi32.LookupPrivilegeValueW(None, "SeShutdownPrivilege", ctypes.byref(luid)):
            return False
        tp = _TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        if not advapi32.AdjustTokenPrivileges(htoken, False, ctypes.byref(tp), 0, None, None):
            return False
        # AdjustTokenPrivileges 即使权限未分配也可能返回 TRUE，需检查错误码
        # ERROR_NOT_ALL_ASSIGNED = 1300
        return kernel32.GetLastError() == 0
    finally:
        kernel32.CloseHandle(htoken)


def power_action(action="shutdown"):
    """直接调用系统 API 执行 关机/重启/睡眠，全程无倒计时横幅提示"""
    if sys.platform != 'win32':
        print("非 Windows 系统，跳过电源操作")
        return False

    if action == "sleep":
        return _sleep_now()

    if not _enable_shutdown_privilege():
        print("未能启用 SeShutdownPrivilege（可能需要以管理员身份运行）")

    if action == "reboot":
        flags = EWX_REBOOT | EWX_FORCEIFHUNG
    else:
        flags = EWX_SHUTDOWN | EWX_POWEROFF | EWX_FORCEIFHUNG

    if ctypes.windll.user32.ExitWindowsEx(flags, 0):
        print(f"电源操作已提交: {action}")
        return True

    print(f"电源操作失败: {action} (错误码 {ctypes.windll.kernel32.GetLastError()})")
    return False


def _sleep_now():
    """让计算机进入睡眠"""
    try:
        ok = ctypes.windll.powrprof.SetSuspendState(False, False, False)
        return bool(ok)
    except Exception as e:
        print(f"睡眠失败: {e}")
        return False
