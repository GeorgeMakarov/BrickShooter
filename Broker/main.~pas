unit main;

interface

uses
  Windows, Messages, SysUtils, Classes, Graphics, Controls, Forms, Dialogs,
  ImgList, Grids, StdCtrls, ExtCtrls;

type

  TCellStatus = (CS_Void,CS_ToLeft,CS_ToRight,CS_ToUp,CS_ToDown,CS_Stand);

  PChecked = ^TChecked;
  TChecked = record
  Coord         :TPoint;
  Next          :PChecked;
  end;

  Cell = record
  Status        :TCellStatus;
  Color         :Word;
  end;

  TCell = Cell;

  TForm1 = class(TForm)
    Button1: TButton;
    Button2: TButton;
    GameField: TImage;
    Button3: TButton;
    Button4: TButton;
    Label1: TLabel;
    Button5: TButton;
    CheckBox1: TCheckBox;
    RadioGroup1: TRadioGroup;
    RadioGroup2: TRadioGroup;
    Label2: TLabel;
    Button6: TButton;
    Label3: TLabel;
    Button7: TButton;
    Label4: TLabel;
    Label5: TLabel;
    Memo1: TMemo;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var Action: TCloseAction);
    procedure Button1Click(Sender: TObject);
    procedure PutBrick(Status:TCellStatus; Color:byte; Coord:TPoint);
    procedure Button2Click(Sender: TObject);
    procedure MoveBrick(Start, Dest:TPoint);
    procedure DrawField;
    procedure DrawGrid;
    procedure GameFieldMouseDown(Sender: TObject; Button: TMouseButton;
      Shift: TShiftState; X, Y: Integer);
    procedure FormActivate(Sender: TObject);
    procedure Button3Click(Sender: TObject);
    procedure Button4Click(Sender: TObject);
    function CheckNeighbourhood(brick:TPoint):boolean;
    procedure DestroyChecked(var FPointer,LPointer:PChecked);
    procedure AddChecked(brick:TPoint);
    function AlreadyChecked(brick:TPoint):boolean;
    function CalcScore(bricks:word):word;
    procedure DeleteBricks;
    procedure Button5Click(Sender: TObject);
    function MoveAfterDelete:boolean;
    procedure CheckBox1Click(Sender: TObject);
    procedure GameFieldMouseMove(Sender: TObject; Shift: TShiftState; X,
      Y: Integer);
    procedure Button6Click(Sender: TObject);
    procedure Button7Click(Sender: TObject);
    function CheckGameOver:boolean;
    function CheckLevelComplete:boolean;
    procedure NewGame;
  private
    { Private declarations }
  public
    { Public declarations }
  end;


const
bricksize = 32;
bmpbricksize=30;
delay = 10;

var
  Form1         : TForm1;
  brick         :Tpicture;
  SourceRect    ,
  TargetRect    :Trect;
  Offset        :TPoint;
  Field         ,
  Undo          :array [0..15,0..15] of TCell;
  FCheckedBricks,
  LCheckedBricks:PChecked;
  score         :word;
  level         :byte;
  bricksameclr  :byte;
  
implementation

{$R *.DFM}

function TForm1.CalcScore(bricks:word):word;
begin
result:=(bricks-3)*2+bricks;
end;

procedure TForm1.DrawGrid;
var
i:byte;
 begin
 with GameField.Canvas do
  begin
  pen.Color:=clsilver;
  for i:=3 to 13 do
   begin
   moveto(i*33,3*33);
   lineto(i*33,13*33);
   moveto(3*33,i*33);
   lineto(13*33,i*33);
   end;
  pen.Color:=clwhite;
  pen.Width:=1;
  MoveTo(33*3-1,33*3-1);
  LineTo(33*13-1,33*3-1);
  LineTo(33*13-1,33*13-1);
  LineTo(33*3-1,33*13-1);
  LineTo(33*3-1,33*3-1);
  end;
 end;

procedure TForm1.MoveBrick(Start, Dest:TPoint);
var
I:word;
R:TRect;
 begin
 R:=Rect(bricksize+1,bricksize+1,bricksize+1,bricksize+1);
 if Start.x=Dest.x then
  begin
  if (dest.y>2) and (dest.y<13) then
  if dest.y>start.y then
  Field[start.x,start.y].Status:=CS_ToDown else
  Field[start.x,start.y].Status:=CS_ToUp;
  i:=start.y;
  while i<>dest.y do
   begin
   if dest.y>start.y then
   Field[Start.x,i+1]:=Field[Start.x,i] else
   Field[Start.x,i-1]:=Field[Start.x,i];
   Field[Start.x,i].Status:=CS_Void;
   DrawField;
   GameField.Repaint;
   sleep(delay);
   if dest.y>start.y then inc(i) else dec(i);
   end;
  end;
 if Start.y=Dest.y then
  begin
  if (dest.x>2) and (dest.x<13) then
  if dest.x>start.x then
  Field[start.x,start.y].Status:=CS_ToRight else
  Field[start.x,start.y].Status:=CS_ToLeft;
  i:=start.x;
  while i<>dest.x do
   begin
   if dest.x>start.x then
   Field[i+1,Start.y]:=Field[i,Start.y] else
   Field[i-1,Start.y]:=Field[i,Start.y];
   Field[i,Start.y].Status:=CS_Void;
   DrawField;
   GameField.repaint;
   sleep(delay);
   if dest.x>start.x then inc(i) else dec(i);
   end;
  end;
 end;

procedure TForm1.PutBrick(Status:TCellStatus; Color:byte; Coord:TPoint);
var
TargetRect,
SourceRect:TRect;
row,col:byte;
 begin
 if Status=CS_void then
 SourceRect:=Rect(0,0,0,0) else
  begin
  row:=Color;
  case Status of
  CS_Stand      : col:=0;
  CS_ToDown     : col:=4;
  CS_ToLeft     : col:=3;
  CS_ToUp       : col:=2;
  CS_ToRight    : col:=1;
  end;
 SourceRect:=Rect(bmpbricksize*col,bmpbricksize*row,bmpbricksize*col+bmpbricksize-1,bmpbricksize*row+bmpbricksize-1);
 end;
 TargetRect:=Rect(coord.x*(bricksize+1),coord.y*(bricksize+1),coord.x*(bricksize+1)+bricksize,coord.y*(bricksize+1)+bricksize);
 GameField.Canvas.CopyRect(TargetRect,brick.Bitmap.Canvas,SourceRect);
 end;

procedure TForm1.AddChecked(brick:TPoint);
var
CheckedBrick:PChecked;
 begin
 inc(bricksameclr);
 New(CheckedBrick);
 CheckedBrick^.Coord:=brick;
 CheckedBrick^.Next:=nil;
 if FCheckedBricks=nil then
  begin
  FCheckedBricks:=CheckedBrick;
  LCheckedBricks:=CheckedBrick;
  end else
  begin
  LCheckedBricks^.Next:=CheckedBrick;
  LCheckedBricks:=CheckedBrick;
  end;
 end;

procedure TForm1.DestroyChecked(var FPointer,LPointer:PChecked);
var
Tmp,Checked:PChecked;
 begin
 Checked:=FPointer;
 if Checked<>nil then
 repeat
 Tmp:=Checked;
 Checked:=Checked^.Next;
 Dispose(Tmp);
 until Checked=nil;
 FPointer:=nil;
 LPointer:=nil;
 bricksameclr:=0;
 end;

function TForm1.AlreadyChecked(brick:TPoint):boolean;
var
Checked:PChecked;
 begin
 result:=false;
 Checked:=FCheckedBricks;
 if Checked<>nil then
 repeat
 if (Checked^.Coord.x=brick.x) and (Checked^.Coord.y=brick.y) then
  begin
  result:=true;
  break;
  end;
 Checked:=Checked^.Next;
 until Checked=nil;
 end;

function TForm1.MoveAfterDelete:boolean;
var
i,j,k:byte;
 begin
 result:=false;
 for i:=0 to 15 do
 for j:=0 to 15 do
  begin
   if (field[i,j].Status=CS_ToLeft) and ((field[i-1,j].Status=CS_Void) or (i-1=2)) then
    begin
    k:=i-1;
    while (field[k,j].Status=CS_Void) do dec(k);
    if k<>2 then
    MoveBrick(point(i,j),point(k+1,j))
    else
     begin
     movebrick(point(1,j),point(0,j));
     movebrick(point(2,j),point(1,j));
     MoveBrick(point(i,j),point(2,j));
     field[2,j].Status:=CS_Stand;
     end;
    result:=true;     
    end;
   if (field[i,j].Status=CS_ToRight) and ((field[i+1,j].Status=CS_Void) or (i+1=13)) then
    begin
    k:=i+1;
    while (field[k,j].Status=CS_Void) do inc(k);
    if k<>13 then
    MoveBrick(point(i,j),point(k-1,j))
    else
     begin
     movebrick(point(14,j),point(15,j));
     movebrick(point(13,j),point(14,j));
     MoveBrick(point(i,j),point(13,j));
     field[13,j].Status:=CS_Stand;
     end;
    result:=true;
    end;
   if (field[i,j].Status=CS_ToUp) and ((field[i,j-1].Status=CS_Void) or (j-1=2)) then
    begin
    k:=j-1;
    while (field[i,k].Status=CS_Void) do dec(k);
    if k<>2 then
    MoveBrick(point(i,j),point(i,k+1))
    else
     begin
     movebrick(point(i,1),point(i,0));
     movebrick(point(i,2),point(i,1));
     MoveBrick(point(i,j),point(i,2));
     field[i,2].Status:=CS_Stand;
     end;
    result:=true;
    end;
   if (field[i,j].Status=CS_ToDown) and ((field[i,j+1].Status=CS_Void) or (j+1=13)) then
    begin
    k:=j+1;
    while (field[i,k].Status=CS_Void) do inc(k);
    if k<>13 then
    MoveBrick(point(i,j),point(i,k-1))
    else
     begin
     movebrick(point(i,14),point(i,15));
     movebrick(point(i,13),point(i,14));
     MoveBrick(point(i,j),point(i,13));
     field[i,13].Status:=CS_Stand;
     end;
    result:=true;
    end;            
  end;
 end;

function TForm1.CheckNeighbourhood(brick:TPoint):boolean;
 begin
 AddChecked(brick);
 result:=false;
 if (not AlreadyChecked(point(brick.x,brick.y-1))) and (brick.y-1<>2) and
    (Field[brick.x,brick.y-1].Color=Field[brick.x,brick.y].Color) and (Field[brick.x,brick.y-1].Status<>CS_Void) then
     begin
      CheckNeighbourhood(Point(brick.x,brick.y-1));
      result:=true;
      end;

 if (not AlreadyChecked(point(brick.x,brick.y+1))) and (brick.y+1<>13) and
    (Field[brick.x,brick.y+1].Color=Field[brick.x,brick.y].Color) and (Field[brick.x,brick.y+1].Status<>CS_Void) then
     begin
     CheckNeighbourhood(Point(brick.x,brick.y+1));
     result:=true;
     end;
 if (not AlreadyChecked(point(brick.x-1,brick.y))) and (brick.x-1<>2) and
    (Field[brick.x-1,brick.y].Color=Field[brick.x,brick.y].Color) and (Field[brick.x-1,brick.y].Status<>CS_Void) then
     begin
     CheckNeighbourhood(Point(brick.x-1,brick.y));
     result:=true;
     end;
 if (not AlreadyChecked(point(brick.x+1,brick.y))) and (brick.x+1<>13) and
    (Field[brick.x+1,brick.y].Color=Field[brick.x,brick.y].Color) and (Field[brick.x+1,brick.y].Status<>CS_Void) then
     begin
     CheckNeighbourhood(Point(brick.x+1,brick.y));
     result:=true;
     end;
 end;

procedure TForm1.FormCreate(Sender: TObject);
var
R:TRect;
begin
score:=0;
FillChar(Field,SizeOf(Field),0);
randomize;
brick:=TPicture.Create;
brick.LoadFromFile('skins\nbricks.bmp');
GameField.Width:=33*16-1;
GameField.Height:=33*16-1;
r:=Rect(0,0,GameField.Width,GameField.Height);
gamefield.Canvas.brush.Color:=0;
gamefield.Canvas.FillRect(r);
drawgrid;
end;

procedure TForm1.FormClose(Sender: TObject; var Action: TCloseAction);
begin
brick.free;
end;

procedure TForm1.Button1Click(Sender: TObject);
var
i,j:byte;
begin
for i:=0 to 15 do
for j:=0 to 15 do
begin
Offset.x:=24*random(4);
offset.y:=24*random(9);
SourceRect:=Rect(offset.x,offset.y,offset.x+23,offset.y+23);
TargetRect:=Rect(i*(bricksize+1),j*(bricksize+1),i*(bricksize+1)+bricksize,j*(bricksize+1)+bricksize);
GameField.Canvas.CopyRect(TargetRect,brick.Bitmap.Canvas,SourceRect);
end;
end;

procedure TForm1.DrawField;
var
i,j,row,col:Word;
r:TRect;
begin
r:=Rect(0,0,Gamefield.Width,GameField.Height);
Gamefield.Canvas.brush.Color:=0;
Gamefield.Canvas.brush.Style:=bsSolid;
Gamefield.Canvas.FillRect(r);
for i:=0 to 15 do
for j:=0 to 15 do
begin
if ((i<3) and (j<3)) or ((i>12) and (j<3)) or ((i<3) and (j>12)) or ((i>12) and (j>12)) then continue;
putbrick(Field[i,j].Status,Field[i,j].Color,point(i,j));
end;
DrawGrid;
//GameField.Repaint;
end;

function TForm1.CheckLevelComplete:boolean;
var i,j:byte;
 begin
 result:=true;
 for i:=3 to 12 do
 for j:=3 to 12 do
 if field[i,j].Status<>CS_Void then
  begin
  result:=false;
  exit;
  end;
 end;

function TForm1.CheckGameOver:boolean;
var i,j:byte;
 begin
 result:=true;
 for i:=3 to 12 do
 if (field[i,3].Status=CS_Void) or (field[3,i].Status=CS_Void) or
    (field[i,12].Status=CS_Void) or (field[12,i].Status=CS_Void) then
  begin
  result:=false;
  exit;
  end;
 end;

procedure TForm1.NewGame;
type
PAdded = ^TAdded;
TAdded = record
coord :tpoint;
next :PAdded;
end;
var
i,j,x,y:word;
Fadded ,
Ladded : PAdded;

function alreadyadded(coord:Tpoint):boolean;
var
added:padded;
 begin
 result:=false;
 added:=fadded;
 if added<>nil then
 repeat
 if (added^.coord.x=coord.x) and (added^.coord.y=coord.y) then
  begin
  result:=true;
  exit;
  end;
 added:=added^.next;
 until added=nil;
 end;

procedure addAdded (Coord:tpoint);
var
added:padded;
 begin
 new(added);
 added^.coord:=Coord;
 added^.next:=nil;
 if fadded=nil then
  begin
  fadded:=added;
  ladded:=added;
  end else
  begin
  ladded^.next:=added;
  ladded:=added;
  end;
 end;

procedure destroyadded;
var
tmp,added:padded;
 begin
 added:=fadded;
 if added<>nil then
 repeat
 tmp:=added;
 added:=added^.next;
 dispose(tmp);
 until added=nil;
 fadded:=nil;
 ladded:=nil;
 end;
begin
if level=0 then
 begin
 score:=0;
 label1.Caption:='0';
 end;
FillChar(Field,sizeof(field),0);
for i:=3 to 12 do
for j:=0 to 2 do
with Field[i,j] do
 begin
 Color:=random(9);
 Status:=CS_Stand;
 end;
for i:=3 to 12 do
for j:=13 to 15 do
with Field[i,j] do
 begin
 Color:=random(9);
 Status:=CS_Stand;
 end;
for i:=0 to 2 do
for j:=3 to 12 do
with Field[i,j] do
 begin
 Color:=random(9);
 Status:=CS_Stand;
 end;
for i:=13 to 15 do
for j:=3 to 12 do
with Field[i,j] do
 begin
 Color:=random(9);
 Status:=CS_Stand;
 end;

i:=0;
Fadded:=nil;
ladded:=nil;
memo1.Lines.Clear;
while i<level+1 do
begin
x:=3+random(10);
y:=3+random(10);
if alreadyadded(point(x,y)) then continue;
addAdded(point(x,y));
memo1.Lines.Add(inttostr(i)+') x = '+inttostr(x)+', y = '+inttostr(y));
with field[x,y] do
 begin
 Color:=random(9);
 Status:=CS_Stand;
 end;
inc(i);
end;
memo1.SelStart:=0;
memo1.SelLength:=0;
destroyadded;
DrawField;
end;

procedure TForm1.Button2Click(Sender: TObject);
begin
level:=0;
label5.caption:='0';
newgame;
end;

procedure TForm1.DeleteBricks;
var
Checked:PChecked;
 begin
 if bricksameclr>2 then
  begin
  inc(score,CalcScore(bricksameclr));
  label1.Caption:=inttostr(score);
  Checked:=FCheckedBricks;
  if Checked<>nil then
  repeat
  Field[Checked^.Coord.x,Checked^.Coord.y].Status:=CS_Void;
  Checked:=Checked^.Next;
  until Checked=nil;
  end;
 end;

procedure TForm1.GameFieldMouseDown(Sender: TObject; Button: TMouseButton;
  Shift: TShiftState; X, Y: Integer);
var
DestPoint:TPoint;
Row,Col:byte;
begin
Col:=trunc(x/33);
Row:=trunc(y/33);
caption:='x = '+inttostr(Col)+', y = '+inttostr(Row);
if (Col=2) or (Col=13) or (Row=2) or (Row=13) then Undo:=Field;
if (Col=2) and (Row>2) and (Row<13) then
 begin
 DestPoint.y:=Row;
 DestPoint.x:=Col+1;
 while (Field[DestPoint.x,DestPoint.y].Status=CS_Void) and (DestPoint.x<13) do inc(DestPoint.x);
 if (DestPoint.x=13) then exit;
 dec(DestPoint.x);
 if DestPoint.x=2 then exit;
 MoveBrick(Point(Col,Row),DestPoint);
 MoveBrick(Point(Col-1,Row),Point(Col,Row));
 MoveBrick(Point(Col-2,Row),Point(Col-1,Row));
 Field[trunc(x/33)-2,Row].Status:=CS_Stand;
 Field[trunc(x/33)-2,Row].Color:=random(9);
// DrawField;
 DestroyChecked(FCheckedBricks,LCheckedBricks);
 CheckNeighbourhood(DestPoint);
 DeleteBricks;
// DrawField;
 end;
if (Col=13) and (Row>2) and (Row<13) then
 begin
 DestPoint.y:=Row;
 DestPoint.x:=Col-1;
 while (Field[DestPoint.x,DestPoint.y].Status=CS_Void) and (DestPoint.x>2) do dec(DestPoint.x);
 if (DestPoint.x=2) then exit;
 inc(DestPoint.x);
 if DestPoint.x=13 then exit;
 MoveBrick(Point(Col,Row),DestPoint);
 MoveBrick(Point(Col+1,Row),Point(Col,Row));
 MoveBrick(Point(Col+2,Row),Point(Col+1,Row));
 Field[Col+2,Row].Status:=CS_Stand;
 Field[Col+2,Row].Color:=random(9);
// DrawField;
 DestroyChecked(FCheckedBricks,LCheckedBricks);
 CheckNeighbourhood(DestPoint);
 DeleteBricks;
// DrawField;
 end;
if (Row=2) and (Col>2) and (Col<13) then
 begin
 DestPoint.y:=Row+1;
 DestPoint.x:=Col;
 while (Field[DestPoint.x,DestPoint.y].Status=CS_Void) and (DestPoint.y<13) do inc(DestPoint.y);
 if (DestPoint.y=13) then exit;
 dec(DestPoint.y);
 if DestPoint.y=2 then exit;
 MoveBrick(Point(Col,Row),DestPoint);
 MoveBrick(Point(Col,Row-1),Point(Col,Row));
 MoveBrick(Point(Col,Row-2),Point(Col,Row-1));
 Field[Col,Row-2].Status:=CS_Stand;
 Field[Col,Row-2].Color:=random(9);
// DrawField;
  DestroyChecked(FCheckedBricks,LCheckedBricks);
 CheckNeighbourhood(DestPoint);
 DeleteBricks;
// DrawField;
 end;
if (Row=13) and (Col>2) and (Col<13) then
 begin
 DestPoint.y:=Row-1;
 DestPoint.x:=Col;
 while (Field[DestPoint.x,DestPoint.y].Status=CS_Void) and (DestPoint.y>2) do dec(DestPoint.y);
 if (DestPoint.y=2) then exit;
 inc(DestPoint.y);
 if DestPoint.y=13 then exit;
 MoveBrick(Point(Col,Row),DestPoint);
 MoveBrick(Point(Col,Row+1),Point(Col,Row));
 MoveBrick(Point(Col,Row+2),Point(Col,Row+1));
 Field[Col,Row+2].Status:=CS_Stand;
 Field[Col,Row+2].Color:=random(9);
// DrawField;
 DestroyChecked(FCheckedBricks,LCheckedBricks);
 CheckNeighbourhood(DestPoint);
 DeleteBricks;
// DrawField;
 end;
while MoveAfterDelete do;
drawfield;
if checkgameover then
 begin
 ShowMessage('game over');
 newgame;
 end;
if CheckLevelComplete then
 begin
 inc(level);
 label5.Caption:=inttostr(level);
 newgame;
 end;
end;

procedure TForm1.FormActivate(Sender: TObject);
begin
repaint
end;

procedure TForm1.Button3Click(Sender: TObject);
begin
left:=0;
top:=0;
Height:=screen.Height;
Width:=screen.Width;
end;

procedure TForm1.Button4Click(Sender: TObject);
begin
Application.Minimize;
end;

procedure TForm1.Button5Click(Sender: TObject);
begin
close;
end;

procedure TForm1.CheckBox1Click(Sender: TObject);
begin
RadioGroup1.Enabled:=CheckBox1.Checked;
RadioGroup2.Enabled:=CheckBox1.Checked;
end;

procedure TForm1.GameFieldMouseMove(Sender: TObject; Shift: TShiftState; X,
  Y: Integer);
 var
 col,row:integer; 
function StatusToStr(st:TCellStatus):string;
 begin
  case st of
  CS_Void       : result:='CS_Void';
  CS_Stand      : result:='CS_Stand';
  CS_ToDown     : result:='CS_ToDown';
  CS_ToLeft     : result:='CS_ToLeft';
  CS_ToUp       : result:='CS_ToUp';
  CS_ToRight    : result:='CS_ToRight';
  end;
 end;
function ColorToStr(clr:byte):string;
 begin
 case clr of
 0 : result := 'red';
 1 : result := 'green';
 2 : result := 'blue';
 3 : result := 'yellow';
 4 : result := 'brown';
 5 : result := 'black';
 6 : result := 'cyan';
 7 : result := 'magenta';
 8 : result := 'rose';
 9 : result := 'orange';
 end;
 end;
begin
Col:=trunc(x/33);
Row:=trunc(y/33);
label2.caption:='x = '+inttostr(Col)+', y = '+inttostr(Row)+' Status = '+StatusToStr(Field[col,row].status)+', Color = '+Colortostr(Field[col,row].color);
end;

procedure TForm1.Button6Click(Sender: TObject);
begin
Field:=Undo;
DrawField;
end;

procedure TForm1.Button7Click(Sender: TObject);
begin
left:=round((screen.Width-841)/2);
top:=round((screen.Height-635)/2);
Height:=635;
Width:=841;
end;

end.
