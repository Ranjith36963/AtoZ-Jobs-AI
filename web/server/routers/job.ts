import { z } from "zod";
import { publicProcedure, router } from "../trpc";

export const jobRouter = router({
  byId: publicProcedure
    .input(z.object({ id: z.number() }))
    .query(async () => {
      // Stub: will be implemented in Stage 2
      // Direct Supabase read — job + company + skills joins
      return null;
    }),
});
