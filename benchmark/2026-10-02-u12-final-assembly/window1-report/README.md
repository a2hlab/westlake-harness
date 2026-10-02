# U12 Stage A window 1 recovery

The missing corpus-v2 manifest was an input-path failure, not a native or JAR verdict. The outer switched the t4 branch and later restored the identical manifest (d5451a892fb7bb58910df68693aa1d96fd7d68465639c2c89fc85c74ad1336f8). All three candidate activation smokes passed before the interruption. The captured facts are preserved verbatim; screenshots require outer review.

The two retained locks had different before_unlock failures: 5cd lost the HDC remote status marker; 61b still had OrganicMaps Android children after both automatic bounded cleanup attempts. Recovery reused the RUNBOOK recipe: batch only the BMS-identified UID/PPID children with immediate kernel identity checks, then stop the parent via begetctl and retry the normal executor finish. No root-parent signal, reboot, identity relaxation or new test was used during recovery.

All three finishes passed: signed U10.1T8, 318 assertions with no differences or absent paths, recovery smoke PASS, final PASS. Both failed-runner locks were then released and all three held checks were empty. RUNTIME is f3b604c94df4 on 5ea/5cd, d6848fa2c989 on 61b; BOOTIMAGE is e3806b65a079. Raw run directories were copied into the versioned input archive and never removed.

The resume keeps the same armed bundle bytes and order, filters already attempted lit-original keys, and starts fresh outputs after real Mac/VM gates and input visibility checks. OrganicMaps has captured t20 evidence but status batch_interrupted; it is not asserted complete or assigned a UI verdict. It is excluded from the immediate resume to avoid repeating the already measured lit-original key, with the interruption explicitly retained in the resume ledger.
