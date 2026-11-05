"""Hand-drawn five-row LED lettering, with a full-height reading corridor."""
import colorsys,math
FONT={
'A':('010','101','111','101','101'),'D':('110','101','101','101','110'),
'E':('111','100','110','100','111'),'G':('111','100','101','101','111'),
'I':('111','010','010','010','111'),'K':('101','101','110','101','101'),
'M':('10001','11011','10101','10001','10001'),
'N':('1001','1101','1101','1011','1001'),
'O':('111','101','101','101','111'),'P':('110','101','110','100','100'),
'R':('110','101','110','101','101'),'S':('111','100','111','001','111'),
'W':('10001','10001','10101','10101','01010'),
' ':('00','00','00','00','00')}
COLORS={'snake':((255,65,0),(255,180,25)), 'mines':((20,100,255),(90,240,255)),
        'pong':((190,20,255),(255,90,155))}
class Marquee:
 def __init__(self,game,text,style):
  self.text=text;self.style=style;self.pixels=set();offset=0
  for letter in text:
   rows=FONT[letter]
   for y,row in enumerate(rows):
    for x,on in enumerate(row):
     if on=='1':self.pixels.add((offset+x,y))
   offset+=len(rows[0])+1
  self.width=offset-1;self.speed=8.;self.lead=.45
  self.duration=self.lead+(14+self.width)/self.speed+.25
  labels=game.labels
  columns=[[labels[k] for k in ('Esc','`','Tab','Caps','L Shift')]]+game.columns
  columns += [[labels[k] for k in ('F11','-','[',"'")], [labels[k] for k in ('F12','=',']')], [labels[k] for k in ('Power','Backspace','\\','Enter','R Shift')]]
  self.cells={(x,y):c for x,col in enumerate(columns) for y,c in enumerate(col)}
 def frame(self,age):
  frame={c:(0,0,0) for c in self.cells.values()}
  if age<self.lead:
   edge=age/self.lead*14
   for (x,y),cell in self.cells.items():
    strength=max(0,1-abs(x-edge)/2)
    frame[cell]=tuple(round(v*strength*.4) for v in self.color(x,y,age))
   return frame
  # A left-to-right banner sweep precedes familiar right-to-left bus lettering.
  # Every complete glyph crosses all ten fully populated central columns.
  scroll=int((age-self.lead)*self.speed);origin=14-scroll
  for (x,y),cell in self.cells.items():
   if (x-origin,y) in self.pixels:frame[cell]=self.color(x,y,age)
  return frame
 def color(self,x,y,age):
  if self.style=='startup':return tuple(round(v*255) for v in colorsys.hsv_to_rgb((x*.065-y*.035-age*.12)%1,.95,1))
  a,b=COLORS[self.style];t=(x+y*.4)/15.6
  return tuple(round(v+(w-v)*t) for v,w in zip(a,b))
