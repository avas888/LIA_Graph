import type { ActorType } from "../graph/types";
import { icons } from "@/shared/ui/icons";

const ACTOR_ICONS: Record<ActorType, string> = {
  curator: icons.actorCurator,
  python: icons.actorPython,
  sql: icons.actorSql,
  llm: icons.actorLlm,
  embedding: icons.actorEmbedding,
};

export function renderActorBadge(actor: ActorType): string {
  return `<span class="orch-actor" data-actor="${actor}" title="${actor}">${ACTOR_ICONS[actor]}</span>`;
}

export function renderActorBadges(actors: ActorType[]): string {
  return actors.map(renderActorBadge).join("");
}
