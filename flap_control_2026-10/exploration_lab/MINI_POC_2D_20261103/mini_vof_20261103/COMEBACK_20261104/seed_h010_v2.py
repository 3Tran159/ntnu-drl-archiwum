"""Construct a V2 initial field from actual fixed-wave and single-phase exports."""
import json
from pathlib import Path
import sys

import numpy as np
from summarize_h010 import col, field
from audit_motion_map import map_vertices, HINGE
from run_day import sha

base, source, destination = map(Path, sys.argv[1:4])
b, target = field(base)
a, flow = field(source)
xyz = target[:,[col(b,f"{axis} (") for axis in "XYZ"]]
source_xy = flow[:,[col(a,f"{axis} (") for axis in "XY"]]
# Undo the small measured displacement of the donor flap before transferring.
source_xy = map_vertices(source_xy,.06678747635)
pres = flow[:,col(a,"Pressure (")]
far = (source_xy[:,0] < -2) & (np.abs(source_xy[:,1])<1)
if not far.any():
    raise ValueError("No upstream pressure datum in donor")
datum = float(np.median(pres[far]))
donor = np.column_stack((flow[:,col(a,"Velocity[i]")]-18,
                         flow[:,col(a,"Velocity[j]")], pres-datum))
def s5(value):
    x = np.clip(value,0,1)
    return x*x*x*(10+x*(-15+6*x))
x,y,_ = xyz.T
weight = s5((x+2)/1.5)*s5((4-x)/2)*s5((1.45-np.abs(y))/.85)
weight *= target[:,col(b,"Volume Fraction")] > .999
delta = np.zeros((len(xyz),3))
indices = np.flatnonzero(weight>0)
for take in np.array_split(indices, max(1,int(np.ceil(len(indices)/128)))):
    dist2 = np.sum((xyz[take,None,:2]-source_xy[None,:,:])**2,axis=2)
    nearest = np.argpartition(dist2, 4, axis=1)[:,:4]
    distance = np.take_along_axis(dist2, nearest, axis=1)
    w = 1/np.maximum(distance,1e-18)
    delta[take] = weight[take,None] * np.sum(donor[nearest]*w[:,:,None],axis=1)/w.sum(axis=1)[:,None]
pabs = target[:,col(b,"Absolute Pressure")]+delta[:,2]
if pabs.min() <= 12339.214766776897 or not np.all(np.isfinite(delta)):
    raise ValueError(f"Seed offline absolute pressure check failed: {pabs.min()} Pa")
seed = np.column_stack((xyz,target[:,col(b,"Velocity[i]")]+delta[:,0],
                         target[:,col(b,"Velocity[j]")]+delta[:,1],
                         target[:,col(b,"Velocity[k]")],
                         target[:,col(b,"Pressure (")]+delta[:,2]))
np.savetxt(destination, seed, delimiter=",", fmt="%.15g",header="X,Y,Z,U,V,W,P",comments="")
destination.with_suffix(".json").write_text(json.dumps({
    "base":str(base),"base_sha256":sha(base),"donor":str(source),"donor_sha256":sha(source),
    "seed_sha256":sha(destination),"donor_gauge_offset_pa":datum,"target_cells":len(xyz),
    "cells_with_donor_correction":len(indices),"estimated_absolute_pressure_min_pa":float(pabs.min()),
    "no_interface_velocity_or_alpha_change":True},indent=2),encoding="utf8")

