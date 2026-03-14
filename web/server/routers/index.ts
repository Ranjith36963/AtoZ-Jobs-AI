import { router } from "../trpc";
import { searchRouter } from "./search";
import { jobRouter } from "./job";
import { facetsRouter } from "./facets";

export const appRouter = router({
  search: searchRouter,
  job: jobRouter,
  facets: facetsRouter,
});

export type AppRouter = typeof appRouter;
