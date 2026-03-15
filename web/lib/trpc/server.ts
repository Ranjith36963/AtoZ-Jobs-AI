import { appRouter } from "@/server/routers";

export function createServerCaller() {
  return appRouter.createCaller({});
}
