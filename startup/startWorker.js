var oShell = WScript.CreateObject("WScript.Shell");
//var oSysEnv = oShell.Environment("SYSTEM");
//oSysEnv("TEST1") = "TEST_VALUE";
var oSysEnv = oShell.Environment("PROCESS");
oSysEnv("PYTHONPATH") = "D:\Git\WMCC Python";
oExec = oShell.Run("python ..\worker\worker.py", 1, true);  