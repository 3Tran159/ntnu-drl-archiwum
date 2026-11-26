// NTNU CFD Mesh Advisor v2 - STAR-CCM+ mesh-only parameter sweep
// 2026-10-28. Draft for validation against YOUR STAR-CCM+ version and .sim.
// Requires 5 length-dimensional global scalar parameters and 4 named reports.
// Default: THREE cases for a smoke test. Deliberately no solver run, no .sim saves.
package macro;

import java.io.*;
import java.util.*;
import star.common.*;
import star.base.report.*;
import star.meshing.*;

public class MeshSweep50 extends StarMacro {

    // SAFETY SETTINGS: only increase CASE_LIMIT to 50 after inspecting first 3 cases.
    private static final int CASE_LIMIT = 3;
    private static final int MAX_CONSECUTIVE_ERRORS = 3;
    private static final int MAX_TOTAL_MINUTES = 600;
    private static final long STOP_IF_CELL_COUNT_ABOVE = 12000000L;
    private static final boolean SAVE_EACH_SIM = false; // reserved; saving is intentionally not implemented

    private static final String[] PARAM_NAMES = {
        "Mesh_Base", "Mesh_Foil", "Mesh_Wake", "Mesh_VOF", "Mesh_LE"
    };
    private static final String[] REPORT_NAMES = {
        "Batch_CellCount", "Batch_MinVolumeChange", "Batch_MinCellQuality", "Batch_MaxSkewness"
    };

    @Override
    public void execute() {
        Simulation sim = getActiveSimulation();
        long campaignStart = System.nanoTime();
        sim.println("[MeshSweep50] Starting MESH-ONLY sweep; CASE_LIMIT=" + CASE_LIMIT);

        if (SAVE_EACH_SIM) {
            sim.println("[MeshSweep50] WARNING: SAVE_EACH_SIM flag is reserved; this macro never writes .sim files.");
        }

        File input = locateCsv("mesh_sweep_50.csv", sim);
        if (input == null || !input.isFile()) {
            sim.println("[MeshSweep50] ABORT: Cannot find mesh_sweep_50.csv. Place it beside the .sim and macro or in the working directory.");
            return;
        }
        File output = new File(input.getParentFile(), "mesh_results.csv");
        sim.println("[MeshSweep50] Input:  " + input.getAbsolutePath());
        sim.println("[MeshSweep50] Output: " + output.getAbsolutePath());

        // Fail before meshing unless the model has been deliberately connected to its controls/reports.
        ScalarGlobalParameter[] params = new ScalarGlobalParameter[PARAM_NAMES.length];
        for (int i = 0; i < PARAM_NAMES.length; i++) {
            try {
                params[i] = (ScalarGlobalParameter) sim.get(GlobalParameterManager.class).getObject(PARAM_NAMES[i]);
                if (params[i] == null) throw new IllegalStateException("Missing parameter");
            } catch (RuntimeException ex) {
                sim.println("[MeshSweep50] ABORT: Missing/invalid scalar global parameter '" + PARAM_NAMES[i] + "': " + ex.getMessage());
                return;
            }
        }
        for (String name : REPORT_NAMES) {
            try {
                if (sim.getReportManager().getReport(name) == null) throw new IllegalStateException("Missing report");
            } catch (RuntimeException ex) {
                sim.println("[MeshSweep50] ABORT: Create a properly configured Report named '" + name + "' before running. " + ex.getMessage());
                return;
            }
        }

        Units meters;
        try {
            meters = (Units) sim.getUnitsManager().getObject("m");
            if (meters == null) throw new IllegalStateException("metre unit missing");
        } catch (RuntimeException ex) {
            sim.println("[MeshSweep50] ABORT: Cannot access length unit m: " + ex.getMessage());
            return;
        }

        MeshPipelineController mesher = sim.get(MeshPipelineController.class);
        int processed = 0;
        int failures = 0;

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(input), "UTF-8"));
             PrintWriter writer = new PrintWriter(new OutputStreamWriter(new FileOutputStream(output), "UTF-8"))) {

            writer.println("case_id,status,cells,min_volume_change,min_cell_quality,max_skew_deg,prism_coverage_pct,mesh_time_s,file_mb,notes");
            writer.flush();
            String line = reader.readLine(); // CSV header
            if (line == null || !line.startsWith("case_id,")) {
                sim.println("[MeshSweep50] ABORT: CSV header mismatch. Expected case_id,base_m,foil_m,wake_m,vof_m,le_m");
                return;
            }

            while (processed < CASE_LIMIT && (line = reader.readLine()) != null) {
                if (line.trim().isEmpty()) continue;
                String[] cols = line.split(",", -1);
                String caseId = (cols.length > 0) ? cols[0].trim() : "UNKNOWN";
                if (cols.length != 6) {
                    writeRow(writer, caseId, "ERROR", null, null, null, null, null, null, null, "Expected 6 CSV fields");
                    failures++;
                    if (failures >= MAX_CONSECUTIVE_ERRORS) break;
                    continue;
                }

                if (elapsedMinutes(campaignStart) >= MAX_TOTAL_MINUTES) {
                    sim.println("[MeshSweep50] Stopping: campaign time budget exceeded.");
                    break;
                }

                double[] v = new double[5];
                try {
                    for (int j = 0; j < 5; j++) {
                        v[j] = Double.parseDouble(cols[j + 1].trim());
                        if (!Double.isFinite(v[j]) || v[j] <= 0 || v[j] > 100.0) {
                            throw new IllegalArgumentException("Invalid length for " + PARAM_NAMES[j]);
                        }
                    }
                } catch (RuntimeException ex) {
                    writeRow(writer, caseId, "ERROR", null, null, null, null, null, null, null, ex.getMessage());
                    failures++;
                    if (failures >= MAX_CONSECUTIVE_ERRORS) break;
                    continue;
                }

                processed++;
                sim.println(String.format(Locale.US,
                    "[MeshSweep50] %s (%d/%d): base=%.6f foil=%.6f wake=%.6f vof=%.6f LE=%.6f [m]",
                    caseId, processed, CASE_LIMIT, v[0], v[1], v[2], v[3], v[4]));

                long meshStart = System.nanoTime();
                try {
                    // IMPORTANT: each parameter must ALREADY be referenced by the actual STAR mesh controls.
                    // Changing a free-standing global parameter does not change a mesh by itself.
                    for (int j = 0; j < 5; j++) {
                        params[j].getQuantity().setValueAndUnits(v[j], meters);
                    }
                    mesher.generateVolumeMesh();
                    double seconds = (System.nanoTime() - meshStart) * 1e-9;

                    Double cells = validReport(sim, "Batch_CellCount");
                    Double volumeChange = validReport(sim, "Batch_MinVolumeChange");
                    Double cellQuality = validReport(sim, "Batch_MinCellQuality");
                    Double skewness = validReport(sim, "Batch_MaxSkewness");
                    Double coverage = validReport(sim, "Batch_PrismCoverage"); // optional report, may be absent

                    boolean complete = cells != null && cells > 0
                        && volumeChange != null && volumeChange >= 0 && volumeChange <= 1
                        && cellQuality != null && cellQuality >= 0 && cellQuality <= 1
                        && skewness != null && skewness >= 0 && skewness <= 180;

                    String status = complete ? "OK" : "INCOMPLETE";
                    String note = complete ? "mesh generated; review QC in workbook"
                                           : "report missing/invalid; verify selection and evaluation";
                    if (cells != null && cells > STOP_IF_CELL_COUNT_ABOVE) {
                        status = "OVER_BUDGET";
                        note = "stopping: high cell count";
                    }
                    writeRow(writer, caseId, status, cells, volumeChange, cellQuality,
                             skewness, coverage, seconds, null, note);
                    sim.println(String.format(Locale.US,
                        "[MeshSweep50] %s: %s; cells=%s; time=%.1fs; VC=%s; skew=%s",
                        caseId, status, fmt(cells), seconds, fmt(volumeChange), fmt(skewness)));
                    failures = 0;

                    if ("OVER_BUDGET".equals(status)) {
                        sim.println("[MeshSweep50] Stopping for RAM protection: cell-count budget exceeded.");
                        break;
                    }
                } catch (Exception ex) {
                    double seconds = (System.nanoTime() - meshStart) * 1e-9;
                    writeRow(writer, caseId, "ERROR", null, null, null, null, null,
                             seconds, null, "mesher exception: " + ex.getClass().getSimpleName() + " " + ex.getMessage());
                    sim.println("[MeshSweep50] ERROR in " + caseId + ": " + ex.toString());
                    failures++;
                    if (failures >= MAX_CONSECUTIVE_ERRORS) {
                        sim.println("[MeshSweep50] Stopping after " + failures + " consecutive failures.");
                        break;
                    }
                }
            }
            sim.println(String.format(Locale.US,
                "[MeshSweep50] FINISHED: processed=%d, elapsed=%.1f min, CSV=%s",
                processed, elapsedMinutes(campaignStart), output.getAbsolutePath()));
        } catch (IOException ex) {
            sim.println("[MeshSweep50] I/O failure: " + ex.toString());
        }
    }

    private static File locateCsv(String name, Simulation sim) {
        File[] candidates = {
            new File(name),
            new File(System.getProperty("user.dir", "."), name),
            new File(sim.getSessionDir(), name)
        };
        for (File candidate : candidates) if (candidate.isFile()) return candidate;
        return null;
    }

    private static Double validReport(Simulation sim, String reportName) {
        try {
            Report report = sim.getReportManager().getReport(reportName);
            if (report == null) return null;
            double val = report.getReportMonitorValue();
            return Double.isFinite(val) ? val : null;
        } catch (Exception ex) {
            return null;
        }
    }

    private static String fmt(Double value) {
        if (value == null || !Double.isFinite(value)) return "";
        return String.format(Locale.US, "%.9g", value);
    }

    private static double elapsedMinutes(long startNs) {
        return (System.nanoTime() - startNs) / 60.0e9;
    }

    private static String safeCsv(String text) {
        if (text == null) return "";
        return "\"" + text.replace("\"", "'").replace("\n", " ").replace("\r", " ") + "\"";
    }

    private static void writeRow(PrintWriter writer, String id, String status,
                                 Double cells, Double volumeChange, Double cellQuality,
                                 Double skewness, Double coveragePct,
                                 Double meshSeconds, Double fileMb, String note) {
        writer.println(id + "," + status + "," + fmt(cells) + "," + fmt(volumeChange)
            + "," + fmt(cellQuality) + "," + fmt(skewness) + "," + fmt(coveragePct)
            + "," + fmt(meshSeconds) + "," + fmt(fileMb) + "," + safeCsv(note));
        writer.flush(); // preserve partial results even if later meshing fails
    }
}
