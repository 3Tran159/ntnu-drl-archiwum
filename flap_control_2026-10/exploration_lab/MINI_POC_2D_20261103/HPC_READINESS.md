# Heavy Validation Lab — IDUN / Sigma2 readiness (no migration started)

Need: active NTNU/IDUN account and permitted allocation; institutional network/SSH access; software licence-group membership and a licence valid on compute nodes. IDUN public documentation lists older STAR modules and a group licence server; it does not verify availability of2606. Ask HPC support/module avail for2606.0002/build21.04.009-R8 Linux. Do not open2606checkpoints in the listed older18.x versions. Existing localPOD permission is not proof of cluster entitlement; confirm licence terms and connectivity before launch.

Use installed Linux-supported MPI matching the STAR build and cluster fabric; do not transfer Windows MS-MPI binaries or assume its command flags. Submit solver through Slurm,never on login nodes. Prepare a single-node test first and confirm native version,MPI launch,licence and memory. Pilot resource request for333939cells could begin at8–16tasks and16–32GiB totalRAM,subject to measured resident memory and allocation; these are untested planning ranges,not a cluster benchmark result.

Transfer viaSSH/SFTP/rsync: immutable full.sim,optional.simh,Java macros,externaltables,motion inputs,configuration and manifests/logs. ComputeSHA256 before and after transfer; preserve originals. Stage into project/scratch appropriate to local retention policy. Open a COPY without reset/remesh,verify physical time,iteration,reports and fields. Use the original production checkpointt1.212s if that continuation is approved; never substitute a benchmark branch. Validate a small restart before any long case. No login,transfer,allocation request or job submission was executed.

Sources checked2026-11-03:
- https://www.hpc.ntnu.no/idun/documentation/idun-for-sintef-and-unity-users/ (STAR modules/licence)
- https://www.hpc.ntnu.no/idun/documentation/login/ (access/login-node role)
- https://documentation.sigma2.no/software/licenses.html (STAR onBetzy,licence-group restrictions)

Pending night priorities: one Mini gap mesh comparison at0;then one dt study onceURANS exists;only then selected fullVOF validation. Each requires separate scientific readiness and free resources; W04 priority persists even at night.
