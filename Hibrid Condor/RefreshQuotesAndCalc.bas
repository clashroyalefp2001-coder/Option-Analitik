Attribute VB_Name = "Module1"
Sub RefreshQuotesAndCalc()
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    ThisWorkbook.RefreshAll
    Application.CalculateFull
    MsgBox "Котировки и расчёты обновлены", vbInformation
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub
