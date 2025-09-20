unit Broker;

interface

uses
  Windows, Messages, SysUtils, Classes, Graphics, Controls, Forms, Dialogs,
  ImgList, Grids, RXGrids, StdCtrls;

type
  TForm1 = class(TForm)
    GameField: TRxDrawGrid;
    Button1: TButton;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var Action: TCloseAction);
    procedure GameFieldDrawCell(Sender: TObject; ACol, ARow: Integer;
      Rect: TRect; State: TGridDrawState);
    procedure GameFieldSelectCell(Sender: TObject; ACol, ARow: Integer;
      var CanSelect: Boolean);
  private
    { Private declarations }
  public
    { Public declarations }
  end;

var
  Form1: TForm1;
  brick:Tpicture;
  SourceRect,TargetRect:Trect;
  Offset:tpoint;

implementation

{$R *.DFM}

procedure TForm1.FormCreate(Sender: TObject);
begin
brick:=TPicture.Create;
brick.LoadFromFile('d:\bricks.bmp');
end;

procedure TForm1.FormClose(Sender: TObject; var Action: TCloseAction);
begin
brick.free;
end;

procedure TForm1.GameFieldDrawCell(Sender: TObject; ACol, ARow: Integer;
  Rect: TRect; State: TGridDrawState);
begin
GameField.Canvas.CopyRect(TargetRect,brick.Bitmap.Canvas,SourceRect);
end;

procedure TForm1.GameFieldSelectCell(Sender: TObject; ACol, ARow: Integer;
  var CanSelect: Boolean);
begin
Offset.x:=24*random(4);
offset.y:=24*random(9);
SourceRect:=Rect(offset.x,offset.y,offset.x+23,offset.y+23);
TargetRect:=Rect(ACol*25,ARow*25,ACol*25+24,ARow*25+24);
end;

end.
