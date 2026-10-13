# Stock187 plus ADC experiment: rejected

The mixed recipe did not preserve BoatAttack geometry. On the actual fresh boot, all seven child-view artifact hashes matched, but three retained SurfaceView buffers were 1200×1920 while bounds and default size were 1920×1200. The original interaction runner rejected the sample before its timed captures and five inputs. The final screenshot shows rendering, which does not establish correct geometry or playability. Popup-after and HW/ZZ candidate smoke were not run.

The candidate was rolled back by the original hook. The baseline boot `362f2212-1a42-4c1a-8487-0dddb091c74b` passed the original 940-object identity selfcheck and original non-file guards; before_unlock returned 0. V2 remains unsealed. See `completion.json` for exact evidence hashes and the durable archive receipt.

The preceding control-flow attempts are preserved in the same archive, including the original holder-format errors, preboot snapshot rejection, automatic restorations, and audit-preserving archive operation. They are not candidate runtime passes.
