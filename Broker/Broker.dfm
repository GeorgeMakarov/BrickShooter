object Form1: TForm1
  Left = 253
  Top = 119
  Width = 633
  Height = 570
  Caption = 'Form1'
  Color = clBtnFace
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -11
  Font.Name = 'MS Sans Serif'
  Font.Style = []
  OldCreateOrder = False
  OnClose = FormClose
  OnCreate = FormCreate
  PixelsPerInch = 96
  TextHeight = 13
  object GameField: TRxDrawGrid
    Left = 72
    Top = 64
    Width = 429
    Height = 429
    BorderStyle = bsNone
    Color = clBlack
    ColCount = 16
    DefaultColWidth = 24
    DefaultRowHeight = 24
    FixedCols = 0
    RowCount = 16
    FixedRows = 0
    Options = [goVertLine, goHorzLine, goColSizing]
    ScrollBars = ssNone
    TabOrder = 0
    OnDrawCell = GameFieldDrawCell
    OnSelectCell = GameFieldSelectCell
  end
  object Button1: TButton
    Left = 224
    Top = 24
    Width = 75
    Height = 25
    Caption = 'Button1'
    TabOrder = 1
  end
end
