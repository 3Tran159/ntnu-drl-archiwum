"""Prescribed motion in radians. Positive +y rotation moves trailing edge toward -z."""
import math,csv,argparse
def harmonic(t,amplitude_rad,frequency_hz,ramp_s,phase_rad=0.0):
 if t<=0:return 0.0,0.0
 q=min(t/ramp_s,1.0)
 r=.5*(1-math.cos(math.pi*q))
 rd=.5*math.pi/ramp_s*math.sin(math.pi*q) if t<ramp_s else 0.0
 w=2*math.pi*frequency_hz; theta=w*t+phase_rad
 return amplitude_rad*r*math.sin(theta),amplitude_rad*(rd*math.sin(theta)+r*w*math.cos(theta))
def rotate(x,z,xh,zh,delta):
 dx=x-xh;dz=z-zh;c=math.cos(delta);s=math.sin(delta)
 return xh+c*dx+s*dz,zh-s*dx+c*dz
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--dt',type=float,default=.0004);a=p.parse_args()
 # Numerical verification fixture, not CFD data or a selected physical frequency.
 with open(a.out,'x',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(['time_local_s','delta_command_rad','omega_command_rad_s'])
  for k in range(1001):
   t=k*a.dt;d,o=harmonic(t,math.radians(.5),1.0,.2);w.writerow([t,d,o])
