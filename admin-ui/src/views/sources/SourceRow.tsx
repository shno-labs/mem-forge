import type { ReactNode } from "react";
import { Info, Loader2, Play, SlidersHorizontal } from "lucide-react";
import type { Source } from "@/api/types";
import { StatusDot } from "@/components/admin/StatusBadge";
import { SyncStatusBar } from "@/components/admin/SyncStatusBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SourceIcon } from "@/components/sources/SourceIcon";
import { timeAgo } from "@/utils/date";
import { sourceActionLayout } from "./sourceActions";

/**
 * One row in the project-grouped sources view. Behaviour and DOM match the
 * flat list that preceded grouping: the row owns the source title, status,
 * counts, sync bar, and the primary configure / sync controls. The overflow
 * menu lives outside this component because its kebab affordance is shared
 * styling that other tests depend on staying in the page module.
 */

export interface SourceRowLabels {
  name: string;
  subtitle?: string;
  description?: string;
}

export function SourceRow({
  source,
  perGroupMemoryCount,
  isSyncing,
  isDeleting,
  isUpdatingSubscription,
  canConfigure,
  isManaged,
  sourceLabel,
  itemLabel,
  authSessionLabel,
  onConfigure,
  onSync,
  onToggleSubscription,
  onShowDetails,
  actionsMenu,
}: {
  source: Source;
  perGroupMemoryCount: number;
  isSyncing: boolean;
  isDeleting: boolean;
  isUpdatingSubscription: boolean;
  canConfigure: boolean;
  isManaged: boolean;
  sourceLabel: SourceRowLabels;
  itemLabel: string;
  authSessionLabel: (status: string) => string;
  onConfigure: () => void;
  onSync: () => void;
  onToggleSubscription: (enabled: boolean) => void;
  onShowDetails: () => void;
  actionsMenu: ReactNode;
}) {
  const enabledLabel = source.enabled_for_me ? "Enabled for me" : "Disabled for me";

  return (
    <div className="space-y-3 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <SourceIcon type={source.type} client={source.client} className="mt-0.5 size-5" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate text-sm font-medium">{source.name}</h3>
              <StatusDot status={source.status} />
              <Badge variant={source.status === "active" ? "secondary" : "outline"}>
                {source.status}
              </Badge>
              {!source.enabled_for_me && <Badge variant="outline">Disabled for me</Badge>}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {sourceLabel.name}
              {sourceLabel.subtitle ? ` · ${sourceLabel.subtitle}` : ""}
            </p>
            {source.type === "agent_session" && (
              <p className="mt-1 text-xs text-muted-foreground">
                Populated automatically by the plugin. No manual sync needed.
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted-foreground">
              <span>
                <span className="font-medium text-foreground">{source.doc_count}</span> {itemLabel}
              </span>
              <span>
                <span className="font-medium text-foreground">{perGroupMemoryCount}</span> memories
              </span>
              <span>
                {source.sync?.status === "running"
                  ? "Syncing now"
                  : `Last synced: ${timeAgo(source.last_sync)}`}
              </span>
              {source.type === "jira" && source.auth_session && (
                <span
                  className={
                    source.auth_session.status === "active"
                      ? "text-emerald-600"
                      : "text-destructive"
                  }
                >
                  Browser session (local adapter): {authSessionLabel(source.auth_session.status)}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 sm:shrink-0">
          <button
            type="button"
            role="switch"
            aria-checked={source.enabled_for_me}
            aria-busy={isUpdatingSubscription}
            aria-label={source.enabled_for_me ? "Disable source for me" : "Enable source for me"}
            title={
              source.enabled_for_me
                ? "This shared source is part of your memory and search context. Turn off to mute it for yourself only — your teammates are not affected."
                : "This shared source is muted for you only. Turn on to include it in your memory and search context — your teammates are not affected."
            }
            disabled={isDeleting || isUpdatingSubscription}
            onClick={() => onToggleSubscription(!source.enabled_for_me)}
            className="inline-flex h-8 items-center gap-2 rounded-lg border border-border bg-background px-2 text-xs font-medium text-muted-foreground transition-colors outline-none hover:border-foreground/20 hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span
              aria-hidden="true"
              className={
                source.enabled_for_me
                  ? "relative inline-flex h-4 w-7 items-center rounded-full bg-emerald-500 transition-colors"
                  : "relative inline-flex h-4 w-7 items-center rounded-full bg-muted-foreground/30 transition-colors"
              }
            >
              {isUpdatingSubscription ? (
                <Loader2 className="absolute left-1/2 top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 animate-spin text-background" />
              ) : (
                <span
                  className={
                    source.enabled_for_me
                      ? "absolute right-0.5 top-0.5 size-3 rounded-full bg-background shadow-sm transition-transform"
                      : "absolute left-0.5 top-0.5 size-3 rounded-full bg-background shadow-sm transition-transform"
                  }
                />
              )}
            </span>
            <span className="hidden lg:inline">{enabledLabel}</span>
          </button>
          {isManaged && (
            <Button
              type="button"
              variant="outline"
              aria-label="View managed source details"
              disabled={isDeleting}
              onClick={onShowDetails}
            >
              <Info className="size-4" />
              <span className="hidden lg:inline">Details</span>
            </Button>
          )}
          {canConfigure && (
            <Button
              type="button"
              variant="outline"
              aria-label="Configure source"
              disabled={isDeleting}
              onClick={onConfigure}
            >
              <SlidersHorizontal className="size-4" />
              <span className="hidden lg:inline">{sourceActionLayout.primary[0].label}</span>
            </Button>
          )}
          {!isManaged && (
            <Button type="button" disabled={isSyncing || isDeleting} onClick={onSync}>
              {isSyncing ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Play className="size-4" />
              )}
              {isSyncing ? "Syncing" : sourceActionLayout.primary[1].label}
            </Button>
          )}
          {actionsMenu}
        </div>
      </div>

      <SyncStatusBar sync={source.sync} itemLabel={itemLabel} onRetry={onSync} />
    </div>
  );
}
