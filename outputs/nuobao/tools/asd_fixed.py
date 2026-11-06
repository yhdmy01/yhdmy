# -*- coding: utf-8 -*-
"""
桌面音箱/闹钟近似建模脚本
Rhino 8 Python 3 / RhinoCommon
运行：在 Rhino 中打开 Python 编辑器，粘贴运行；脚本会把模型保存到当前用户桌面的 pelican_speaker_model.3dm
单位：mm
"""
import math
import os
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import Rhino.Geometry as rg
from System.Drawing import Color

# -----------------------------
# 基本尺寸（依据照片按比例估计）
# -----------------------------
W = 180.0                 # 宽
D = 78.0                  # 深
H = 118.0                 # 高
R = 22.0                  # 外壳圆角半径
FRONT_Y = -D/2.0
BACK_Y = D/2.0

# -----------------------------
# 图层和材质
# -----------------------------
def ensure_layer(name, color):
    if not rs.IsLayer(name):
        rs.AddLayer(name, color)
    else:
        rs.LayerColor(name, color)
    return name

LAYERS = {
    'Shell': ensure_layer('01_Shell_LightBlue', Color.FromArgb(155, 213, 222)),
    'Panels': ensure_layer('02_Front_Back_Panels', Color.FromArgb(35, 42, 47)),
    'Controls': ensure_layer('03_Top_Controls', Color.FromArgb(248, 245, 235)),
    'Grille': ensure_layer('04_Back_Grille', Color.FromArgb(190, 224, 230)),
    'Feet': ensure_layer('05_Feet', Color.FromArgb(246, 240, 224)),
    'Details': ensure_layer('06_Details', Color.FromArgb(82, 96, 102)),
}

MAT_CACHE = {}
def material(name, color, gloss=0.35):
    if name in MAT_CACHE:
        return MAT_CACHE[name]
    mat = Rhino.DocObjects.Material()
    mat.Name = name
    mat.DiffuseColor = color
    mat.SpecularColor = Color.FromArgb(255,255,255)
    mat.ReflectionColor = Color.FromArgb(255,255,255)
    # RhinoCommon uses Shine (0-255), not Glossiness.
    mat.Shine = int(max(0.0, min(1.0, gloss)) * 255)
    idx = sc.doc.Materials.Add(mat)
    MAT_CACHE[name] = idx
    return idx

MATS = {
    'blue': material('Pastel light blue shell', Color.FromArgb(157, 215, 223), 0.78),
    'black': material('Front dark glass', Color.FromArgb(12, 18, 24), 0.78),
    'white': material('Warm white plastic', Color.FromArgb(244, 240, 226), 0.54),
    'grille': material('Blue grille insert', Color.FromArgb(179, 213, 220), 0.38),
    'dark': material('Grille holes / rubber', Color.FromArgb(24, 38, 43), 0.25),
    'label': material('Rear label', Color.FromArgb(90, 103, 101), 0.25),
}

def set_obj(obj_id, layer, mat_key=None, name=None):
    if not obj_id:
        return obj_id
    rs.ObjectLayer(obj_id, layer)
    if mat_key:
        rs.ObjectMaterialIndex(obj_id, MATS[mat_key])
    if name:
        rs.ObjectName(obj_id, name)
    return obj_id

# -----------------------------
# 几何辅助
# -----------------------------
def rounded_points(w, h, r, plane='xz', fixed=0.0, cx=0.0, cy=0.0, cz=0.0, n=8):
    """返回圆角矩形闭合点列。plane='xz' 时固定 y；plane='xy' 时固定 z。"""
    r = min(r, w/2.0-0.01, h/2.0-0.01)
    corners = [(w/2-r, h/2-r, 0), (-w/2+r, h/2-r, 90), (-w/2+r, -h/2+r, 180), (w/2-r, -h/2+r, 270)]
    points=[]
    for x0, z0, start in corners:
        for i in range(n+1):
            a=math.radians(start+i*90.0/n)
            x=x0+r*math.cos(a); z=z0+r*math.sin(a)
            if plane=='xz': points.append(rg.Point3d(cx+x, fixed, cz+z))
            else: points.append(rg.Point3d(cx+x, cy+z, fixed))
    points.append(points[0])
    return points

def rounded_extrusion_xz(w,h,r,y,depth,layer,mat_key,name):
    pts=rounded_points(w,h,r,'xz',fixed=y)
    crv=rg.PolylineCurve(pts)
    brep=rg.Extrusion.Create(crv, rg.Vector3d(0,depth,0), True)
    return set_obj(sc.doc.Objects.AddBrep(brep),layer,mat_key,name)

def rounded_extrusion_xy(w,d,r,z,depth,layer,mat_key,name):
    pts=rounded_points(w,d,r,'xy',fixed=z)
    crv=rg.PolylineCurve(pts)
    brep=rg.Extrusion.Create(crv, rg.Vector3d(0,0,depth), True)
    return set_obj(sc.doc.Objects.AddBrep(brep),layer,mat_key,name)

def box(x0,y0,z0,x1,y1,z1,layer,mat_key,name):
    pts=[rg.Point3d(x0,y0,z0),rg.Point3d(x1,y0,z0),rg.Point3d(x1,y1,z0),rg.Point3d(x0,y1,z0),rg.Point3d(x0,y0,z1),rg.Point3d(x1,y0,z1),rg.Point3d(x1,y1,z1),rg.Point3d(x0,y1,z1)]
    idx=[[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[4,0,3,7]]
    brep=rg.Brep.CreateFromBox(pts)
    return set_obj(sc.doc.Objects.AddBrep(brep),layer,mat_key,name)

def cylinder(x,y,z,r,depth,axis,layer,mat_key,name,cap=True):
    pl=rg.Plane(rg.Point3d(x,y,z),axis)
    cyl=rg.Cylinder(rg.Circle(pl,r),depth)
    return set_obj(sc.doc.Objects.AddBrep(cyl.ToBrep(cap,cap)),layer,mat_key,name)

def text(txt, x,y,z, height, layer, mat_key='dark', name=None):
    pl=rg.Plane(rg.Point3d(x,y,z),rg.Vector3d(0,1,0),rg.Vector3d(0,0,1))
    crv=rg.TextEntity.Create(txt,pl,height, 'Arial', False, False)
    return set_obj(sc.doc.Objects.AddText(crv),layer,mat_key,name)

# -----------------------------
# 主体外壳
# -----------------------------
rs.EnableRedraw(False)
rs.Command('_-SetDocumentUserText ModelDescription "Approximate desktop speaker from reference photos" _Enter', False)
body = rounded_extrusion_xz(W,H,R,FRONT_Y,D,'01_Shell_LightBlue','blue','Main rounded speaker shell')

# 底部浅色分界带（模拟照片下半部渐变/接缝）
rounded_extrusion_xz(W-3,38,15,FRONT_Y-0.8,2.0,'01_Shell_LightBlue','blue','Lower shell seam')

# 正面黑色面板：保持浅色边框
front = rounded_extrusion_xz(W-18,H-25,18,FRONT_Y-2.2,2.6,'02_Front_Back_Panels','black','Front dark glass display panel')
# 面板边缘的浅色内框（薄边）
rounded_extrusion_xz(W-23,H-30,15,FRONT_Y-1.5,1.2,'02_Front_Back_Panels','white','Front inner bezel')
# 黑面再次覆盖，形成黑色内窗
rounded_extrusion_xz(W-29,H-36,13,FRONT_Y-2.8,1.8,'02_Front_Back_Panels','black','Front black inner window')

# 正面小孔/指示点
cylinder(-62, FRONT_Y-4.0, 5, 2.3, 1.0, rg.Vector3d(0,1,0), '06_Details','dark','Front status dot')

# 顶部控制条、长按钮、左右小键
rounded_extrusion_xy(92,16,7, H+1.0, 5.0,'03_Top_Controls','white','Top long control bar')
rounded_extrusion_xy(28,12,5, H+6.0, 3.5,'03_Top_Controls','white','Top center key')
for x in (-35,-12,14,36):
    cylinder(x,0,H+6.0,3.2,3.2,rg.Vector3d(0,0,1),'03_Top_Controls','white','Top control key')
# 顶部中央凸起拨杆
box(-7,-4,H+8.5,7,4,H+15.5,'03_Top_Controls','white','Top raised switch')

# 后部扬声器面板
rounded_extrusion_xz(124,69,18,BACK_Y+0.8,2.4,'04_Back_Grille','grille','Rear grille plate')
# 背部孔阵列，孔做成深色圆柱凹孔视觉件
cols, rows = 18, 8
for j in range(rows):
    z = -31 + j*9.0
    offset = 4.5 if j%2 else 0
    for i in range(cols):
        x = -59 + i*7.0 + offset
        # 用椭圆范围裁切出圆角阵列轮廓
        if (x/61.0)**2 + (z/33.0)**2 <= 1.03:
            cylinder(x,BACK_Y+3.0,z,2.35,1.6,rg.Vector3d(0,-1,0),'04_Back_Grille','dark','Rear grille opening')

# 后部上下两条装饰/信息条
rounded_extrusion_xz(92,12,5,BACK_Y+3.1,1.8,'06_Details','white','Rear upper label strip')
text('AI SMART SPEAKER', -43, BACK_Y+5.2, -46, 3.0, '06_Details','label','Rear product marking')
text('MODEL  N5S', -25, BACK_Y+5.2, -51, 2.3, '06_Details','label','Rear model marking')

# 左右侧浅色小旋钮/挂耳（照片侧视可见）
for x in (-W/2-1.0, W/2+1.0):
    cylinder(x, 0, 17, 7.0, 7.0, rg.Vector3d(1 if x<0 else -1,0,0),'03_Top_Controls','white','Side small button')

# 四个脚垫：前后各两只
for x in (-61,61):
    for y in (-23,23):
        cylinder(x,y,-8,8,13,rg.Vector3d(0,0,1),'05_Feet','white','Rubber foot')
        cylinder(x,y,-9,6.5,2,rg.Vector3d(0,0,1),'05_Feet','blue','Foot collar')

# 选择集/文档信息
rs.SelectObjects([body])
sc.doc.Views.Redraw()
rs.EnableRedraw(True)

# 保存到桌面，若桌面不可用则保存到当前工作目录
home = os.path.expanduser('~')
desktop = os.path.join(home, 'Desktop')
if not os.path.isdir(desktop): desktop = home
path = os.path.join(desktop, 'pelican_speaker_model.3dm')
try:
    rs.Command('_-SaveAs "{}" _Enter'.format(path.replace('\\','/')), False)
except Exception:
    print('模型已生成，但自动保存失败，请手动执行 SaveAs。')
print('完成：{}'.format(path))
