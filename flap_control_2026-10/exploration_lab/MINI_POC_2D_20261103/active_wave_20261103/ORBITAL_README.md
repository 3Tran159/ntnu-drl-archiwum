# ORBITAL-FORCING URANS — pending native field diagnostic

User confirmed head seas and deep water. Config and target CSV define a wave measured locally at hinge,not at inlet. In Mini frame,head waves propagate+x while ship forward is-x. Atcrest theta_h=0,u perturbation positive,v=0 becoming downward. theta=omega_e*t-k*(x-x_h). All amplitudes use intrinsicomega; only phase evolves at encounteromega.

Analytic divergence and inviscid momentum residual tests pass. This is not a CFD verification. An inlet-only convected signal would have k_adv=omega_e/U and phase error~54.5degrees across the old inlet-to-hinge distance; it is not the required local field. Old top/bottomsymmetry also blocks orbital vertical velocity. Old domain extends above notional free surface and cannot host the unmodified Airy exponential.

Next native diagnostic must be an empty,fully submerged2D domain,e.g y[-1.19,1.19]m with sea levely_h+2,matching orbital velocity at inlet and matchingpressure/open backflow conditions at otherboundaries. Compare probes near hinge and upstream/downstream with prescribed phase,amplitudes,and spatial variation before adding foil or interpreting forces. No domain/BC change may be hidden between W0 andWA2.

Use short smooth turn-on envelope with zeroendpoint derivatives; ramp the incident field consistently invelocityandpressure,or initialize a compatible orbital field; analytic full-amplitude pressure formula alone is not valid during arbitrary amplitude ramps. Derive ramp pressure from velocity potential Bernoulli before activation.

C0/W0/WA2 must share the same mesh,domain,numerics; only forcing/control differ. For active case startA2deg,phase0 locally at hinge,after kinematic tests. ±5deg and extra phases are unapproved until safety review. Mh axis-z matches positive flap direction,soMh*delta_dot is signed fluid power to flap,not full boat power.

No VOF,training,or night run has been started. Night experiment requires explicit user selection,resource check,and a native short-testPASS.
