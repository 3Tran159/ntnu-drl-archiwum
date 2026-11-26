# MINI_POC_2D — working notes

Main model: gap_delta_0 and gap_delta_2. Native NACA66-012 MOD main/flap polygons from protected campaign, hinge(.952,.0212817328)m; clearance2.5mm. Static poses get independent true2D meshes. No Overset/VOF. Sealed_demo_delta_0 is a separate algorithm demonstrator. Sealed+2 failed mesh quality and is BLOCKED; no .sim was built from it.

Physics: steady incompressible SST k-omega/all-y+,rho1000kg/m3,mu.001Pa.s,U18m/s,Re21.42million,I.001,viscosityratio10,second-order space. Coordinates map old(x,z) to new(x,y). Uniform reference absolute pressure120736.226Pa equals old hydrostatic ambient near hinge. Gravity is omitted: coefficients contain no buoyancy. This is a fidelity change from the older gravity/VOF models and is not a direct C01 validation.

Domain x[-5.95,11.9],y[-5.95,5.95]m; inlet left,outlet right,top/bottom symmetry. Boundary sensitivity remains unverified. Full native profile vertices preserved. Gmsh 2D wall layers:20micrometre first layer,ratio1.2,total.9mm; special fans at sharp TE. Gap size target.25mm(~10 cells across the nominal gap away from layers). Native y+ and local gap resolution must be checked after solve. Minimum signedGmshSICN~.016 main; coarse sealed~.0044, especially weak TE elements. Positive elements do not establish mesh convergence.

Forces and Mh are per unit span. qS=192780N per1m reference depth. CL=Fy/qS,CD=Fx/qS. Mh uses flap wall only,hinge origin and axis-z,matching the original+y moment convention;positive delta rotates TE down. Future actuator-power signs must be tested before rewards are defined.

Built files: <case>/MINI_prepared.sim. Never overwrite them with a result. SolveMini.java exports history.csv,Cp_yplus.csv,residual_*.csv,MINI_result.sim and SOLVE_STATUS.json. Guarded single run: Python run_one.py gap_delta_0 (or gap_delta_2 after reviewing0). Existing histories prevent replay. Five-minute solver budget excludes startup/load/save. pABS floor12339.2147668Pa,positive mesh,facevalidity>=.5,turbulence floors andcaps preserved. Force stabilization requires adjacent25iteration windows;mass<1e-4 and residual reduction<=.01 are acceptance gates. An early steady iterate is not a measurement.

Stop: create STOP_MINI.json in this directory; solver checks every iteration and saves. Do not delete a resource/physical HOLD marker automatically. No Windows startup or scheduled auto-launch was installed. The older STOP_OWNED_CFD.json remains intact and blocks the old campaign; this explicitly authorized independent case is not a release of old FAILs.

Next: finish0; if safe and stable,run+2. Then review force trend and cost. Static-2/-5/+5 remain pending; harmonic±2/±5,VOF,surrogate,DRL remain later gated stages. Night queue remains existing queue,paused: no automatic22:00start and no heavy local runs while W04 conflicts.

Native2D reporting correction: CellQuality is unavailable in the true2D field list. SolveMini removes that unset3D report and uses nativeLeastSquaresQuality>0,FaceValidity>=.5,Volume>0 together with positive signedGmshSICN. CellQualityRemediation model is enabled in the solve copy; the prepared immutable files retain their original physics setup. API-error attempts are archived; the current test continues their saved flow fields and does not qualify their early iterates as data.
