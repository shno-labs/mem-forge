import type { ReactNode } from "react";
import { Info, Loader2, Play, SlidersHorizontal } from "lucide-react";
import type { Source, SourceCapabilities, SourceOwnership } from "@/api/types";
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
 *
 * Action visibility is driven entirely by `source.capabilities` returned by
 * the backend. When the viewer can only subscribe (a non-manager looking at
 * a shared source), the row collapses to a subscription-oriented card
 * without management controls.
 */

export interface SourceRowLabels {
  name: string;
  subtitle?: string;
  description?: string;
}

const DEFAULT_CAPABILITIES: SourceCapabilities = {
  can_subscribe: false,
  can_configure: false,
  can_sync: false,
  can_force_resync: false,
  can_delete: false,
};

export function SourceRow({
  source,
  perGroupMemoryCount,
  isSyncing,
  isDeleting,
  isManaged,
  sourceLabel,
  itemLabel,
  authSessionLabel,
  enabledForMe,
  isSubscriptionPending,
  onConfigure,
  onSync,
  onShowDetails,
  onSubscriptionChange,
  actionsMenu,
}: {
  source: Source;
  perGroupMemoryCount: number;
  isSyncing: boolean;
  isDeleting: boolean;
  isManaged: boolean;
  sourceLabel: SourceRowLabels;
  itemLabel: string;
  authSessionLabel: (status: string) => string;
  enabledForMe: boolean;
  isSubscriptionPending: boolean;
  onConfigure: () => void;
  onSync: () => void;
  onShowDetails: () => void;
  onSubscriptionChange: (enabled: boolean) => void;
  actionsMenu: ReactNode;
}) {
  const capabilities = source.capabilities ?? DEFAULT_CAPABILITIES;
  const ownershipText = formatOwnership(source.ownership);
  const hasManagementControl =
    capabilities.can_configure || capabilities.can_sync || isManaged;

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
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {sourceLabel.name}
              {sourceLabel.subtitle ? ` · ${sourceLabel.subtitle}` : ""}
            </p>
            {ownershipText && (
              <p className="mt-1 text-xs text-muted-foreground">{ownershipText}</p>
            )}
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
              {source.type === "jira" && source.auth_session && hasManagementControl && (
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

        <div className="flex items-center justify-end gap-2 sm:shrink-0">
          {capabilities.can_subscribe && (
            <SubscriptionToggle
              sourceName={source.name}
              enabled={enabledForMe}
              pending={isSubscriptionPending}
              onChange={onSubscriptionChange}
            />
          )}
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
          {capabilities.can_configure && (
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
          {capabilities.can_sync && !isManaged && (
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

      {hasManagementControl && (
        <SyncStatusBar sync={source.sync} itemLabel={itemLabel} onRetry={onSync} />
      )}
    </div>
  );
}

function SubscriptionToggle({
  sourceName,
  enabled,
  pending,
  onChange,
}: {
  sourceName: string;
  enabled: boolean;
  pending: boolean;
  onChange: (enabled: boolean) => void;
}) {
  return (
    <label
      className="flex items-center gap-2 rounded-md border bg-background px-2.5 py-1 text-xs"
      title={`Toggle whether memories from "${sourceName}" appear in your views`}
    >
      <input
        type="checkbox"
        className="size-3.5"
        aria-label={`Enable "${sourceName}" for me`}
        checked={enabled}
        disabled={pending}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="text-muted-foreground">
        {pending ? "Saving..." : "Enabled for me"}
      </span>
    </label>
  );
}

function formatOwnership(ownership: SourceOwnership | undefined): string {
  if (!ownership) return "";
  const creator = ownership.created_by_user_id;
  if (ownership.viewer_relationship === "creator") {
    return "Created by you";
  }
  if (ownership.viewer_relationship === "workspace_admin") {
    if (!creator) return "You manage as workspace admin";
    return `Created by ${creator} · You manage as workspace admin`;
  }
  if (creator) return `Created by ${creator}`;
  return "";
}
