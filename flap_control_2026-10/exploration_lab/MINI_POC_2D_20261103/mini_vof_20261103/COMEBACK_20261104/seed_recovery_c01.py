"""Transfer the settled C01 disturbance onto Mini's native flat-water initial fields."""
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/"recovery_v3_deps"))
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree

from run_day import sha
from summarize_h010 import col, field

def smooth(v):
    q = np.clip(v,0,1)
    return q**3*(10+q*(-15+6*q))

def prepare(source, native, destination):
    a, donor = field(source)
    b, base = field(native)
    xyz=base[:,[col(b,k+" (") for k in "XYZ"]]
    x,y,z=xyz.T
    xo=donor[:,col(a,"X (")]
    zo=donor[:,col(a,"Z (")]
    donor_xy=np.column_stack((xo,zo))
    target_xy=np.column_stack((x,y-.02128173276777*smooth((y-.25)/1.45)))
    source_water=donor[:,col(a,"Volume Fraction")]
    target_water=base[:,col(b,"Volume Fraction")]
    pabs=donor[:,col(a,"Absolute Pressure")]
    depth=2-zo
    hydro=101325+9.81*np.where(depth>=0,1000.,1.2)*depth
    variables=np.column_stack((donor[:,col(a,"Velocity[i]")],donor[:,col(a,"Velocity[k]")],
                 pabs-hydro,np.log(donor[:,col(a,"Turbulent Kinetic Energy")]),
                 np.log(donor[:,col(a,"Specific Dissipation Rate")])))
    if not np.isfinite(variables).all():
        raise ValueError("Nonfinite C01 source fields")
    taper=smooth((x+12)/5)*smooth((28-x)/5)*smooth((y+10)/3)*smooth((4-y)/.8)
    result=np.column_stack((np.full(len(x),18.),np.zeros(len(x)),base[:,col(b,"Pressure (")],
        np.full(len(x),np.log(.000486)),np.log(3.24+45.36*target_water)))
    extrapolated=0
    for src_mask, target_mask in ((source_water>.999,target_water>.999),
                                  (source_water<.001,target_water<.001)):
        src_mask &= (xo>-14)&(xo<30)&(zo>-12)&(zo<5)
        take=np.flatnonzero(target_mask & (taper>0))
        points, values=donor_xy[src_mask],variables[src_mask]
        xy=target_xy[take]
        interpolator=LinearNDInterpolator(points,values)
        samples=interpolator(xy)
        invalid=~np.isfinite(samples).all(axis=1)
        if invalid.any():
            distance,index=cKDTree(points).query(xy[invalid],k=6)
            weights=1/np.maximum(distance,1e-9)**2
            samples[invalid]=(values[index]*weights[:,:,None]).sum(axis=1)/weights.sum(axis=1)[:,None]
            extrapolated+=int(invalid.sum())
        weight=taper[take,None]
        samples[:,2]+=result[take,2]
        result[take]+=(samples-result[take])*weight
    p_initial=base[:,col(b,"Absolute Pressure")]+result[:,2]-base[:,col(b,"Pressure (")]
    if p_initial.min()<=12339.214766776897 or not np.isfinite(result).all():
        raise ValueError(f"Mapped seed failed offline pABS/finite gate: {p_initial.min():g} Pa")
    table=np.column_stack((xyz,result[:,:2],np.zeros(len(x)),result[:,2],np.exp(result[:,3:5])))
    np.savetxt(destination,table,delimiter=",",fmt="%.16g",header="X,Y,Z,U,V,W,P,K,O",comments="")
    destination.with_suffix(".json").write_text(json.dumps(dict(source=str(source),source_sha256=sha(source),
        base=str(native),base_sha256=sha(native),seed_sha256=sha(destination),cells=len(x),
        pABS_min_estimate_pa=float(p_initial.min()),seed_speed_max=float(np.hypot(result[:,0],result[:,1]).max()),
        k_min=float(np.exp(result[:,3]).min()),omega_min=float(np.exp(result[:,4]).min()),
        nearest_fallback_cells=extrapolated,alpha_from="Mini native flat",out_of_plane_velocity_m_s=0,
        pressure="C01 absolute minus donor hydrostatic, added once to Mini native reduced pressure"),indent=2))

if __name__=="__main__":
    prepare(*map(Path,sys.argv[1:]))

