<script lang="ts">
  import { onMount } from 'svelte';
  import { sampleAssessment, severityOrder } from '$lib/assessment';
  import type { ClusterAssessment, IncidentAssessment, Severity } from '$lib/assessment';

  type ViewState = 'ready' | 'loading' | 'error';

  let viewState = $state<ViewState>('ready');
  let assessment = $state<ClusterAssessment>(sampleAssessment);
  let selectedIncidentIndex = $state(0);
  let commandCopied = $state(false);
  let liveSource = $state('sample context');
  let errorMessage = $state('');
  let hasLoadedLiveAssessment = $state(false);
  let isRefreshing = $state(false);

  const activeIncidents = $derived(
    [...assessment.incidents].sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity])
  );
  const selectedIncident = $derived<IncidentAssessment | null>(
    activeIncidents[selectedIncidentIndex] ?? activeIncidents[0] ?? null
  );
  const selectedEvidence = $derived(selectedIncident?.evidence ?? []);
  const affectedResourceCount = $derived(
    new Set(activeIncidents.flatMap((incident) => incident.affected_resources)).size
  );
  const highSeverityCount = $derived(
    activeIncidents.filter((incident) => ['critical', 'high'].includes(incident.severity)).length
  );
  const commandPreview = $derived(selectedIncident?.safe_next_steps[0] ?? 'sre-cli assess --context-file context.json');
  const selectedTitle = $derived(selectedIncident ? readableTitle(selectedIncident) : 'No incident selected');
  const selectedCause = $derived(selectedIncident ? readableCause(selectedIncident) : 'No action needed right now.');
  const metrics = $derived([
    { label: 'Cluster health', value: assessment.severity === 'info' ? 'Quiet' : 'Degraded' },
    { label: 'Active issues', value: activeIncidents.length.toString() },
    { label: 'Urgent', value: highSeverityCount.toString() },
    { label: 'Affected', value: affectedResourceCount.toString() },
    { label: 'Evidence', value: assessment.evidence_count.toString() },
    { label: 'Window', value: 'Live' }
  ]);

  onMount(() => {
    void refreshAssessment();
  });

  async function refreshAssessment() {
    if (hasLoadedLiveAssessment) {
      isRefreshing = true;
    } else {
      viewState = 'loading';
    }
    errorMessage = '';
    try {
      const response = await fetch('/api/assessment');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error ?? 'Unable to load assessment');
      }
      assessment = payload.assessment;
      liveSource = `${payload.source} / ${payload.namespace}`;
      selectedIncidentIndex = 0;
      hasLoadedLiveAssessment = true;
      viewState = 'ready';
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Unable to load assessment';
      if (!hasLoadedLiveAssessment) {
        viewState = 'error';
      }
    } finally {
      isRefreshing = false;
    }
  }

  function selectIncident(index: number) {
    selectedIncidentIndex = index;
    commandCopied = false;
  }

  async function copyCommand() {
    commandCopied = true;
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(commandPreview);
    }
  }

  function readableTitle(incident: IncidentAssessment) {
    if (incident.likely_cause.includes('STRIPE_API_KEY')) {
      return 'checkout-api missing STRIPE_API_KEY';
    }
    return incident.title
      .replace(' reported by K8sGPT', '')
      .replace('Deployment/', '')
      .replace('Service/', '')
      .replace('PVC/', '')
      .replace('Node/', 'Node ')
      .replace('Pod/', 'Pod ');
  }

  function readableCause(incident: IncidentAssessment) {
    if (incident.likely_cause.includes('STRIPE_API_KEY')) {
      return 'The pod exits immediately because the deployment does not provide the Stripe API key environment variable.';
    }
    if (incident.likely_cause.includes('minimum availability')) {
      return 'The deployment is below its availability target. Check the newest pod failures before rolling forward.';
    }
    if (incident.likely_cause.includes('NotReady')) {
      return 'A node is not ready. Workloads scheduled there may be unavailable or stuck pending.';
    }
    return incident.likely_cause;
  }

  function readableEvidence(detail: string) {
    if (detail.includes('STRIPE_API_KEY')) {
      return detail.includes('Fix:')
        ? 'Restore the Secret or deployment environment reference for STRIPE_API_KEY.'
        : 'Runtime output points to a missing STRIPE_API_KEY environment variable.';
    }
    return detail;
  }

  function severityClasses(severity: Severity) {
    return {
      critical: 'border-red-400/65 bg-red-500/12 text-red-100',
      high: 'border-amber-300/65 bg-amber-400/12 text-amber-100',
      medium: 'border-sky-300/55 bg-sky-400/10 text-sky-100',
      low: 'border-zinc-600/45 bg-white/4 text-zinc-300',
      info: 'border-zinc-700/45 bg-white/3 text-zinc-400'
    }[severity];
  }

  function severityRail(severity: Severity) {
    return {
      critical: 'bg-red-300',
      high: 'bg-amber-300',
      medium: 'bg-sky-300',
      low: 'bg-zinc-700',
      info: 'bg-zinc-800'
    }[severity];
  }
</script>

<svelte:head>
  <title>Cluster Triage</title>
  <meta name="description" content="Kubernetes incident triage for local SRE assessment." />
</svelte:head>

<main class="min-h-[100dvh] bg-[#030303] px-4 py-6 text-zinc-200 sm:px-6">
  <section class="mx-auto grid max-w-[1360px] gap-3">
    <header class="overflow-hidden rounded-xl border border-white/10 bg-[#070707]/95 shadow-xl shadow-black/10">
      <div class="flex h-14 items-center justify-between border-b border-white/10 px-4">
        <div class="min-w-0">
          <h1 class="text-base font-medium tracking-[-0.02em] text-zinc-100">Cluster triage</h1>
          <p class="mt-0.5 truncate text-xs text-zinc-500">{liveSource}</p>
        </div>

        <div class="flex items-center gap-2">
          <span class={`mono border px-2.5 py-1.5 text-[0.68rem] uppercase tracking-[0.16em] ${severityClasses(assessment.severity)}`}>
            {assessment.severity}
          </span>
          <button class="rounded-md border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-zinc-300 hover:bg-white/[0.06] disabled:opacity-60" onclick={refreshAssessment} disabled={isRefreshing}>
            {isRefreshing ? 'Refreshing' : 'Refresh'}
          </button>
        </div>
      </div>

      <div class="grid grid-cols-2 divide-x divide-y divide-white/10 sm:grid-cols-3 lg:grid-cols-6 lg:divide-y-0">
        {#each metrics as metric (metric.label)}
          <div class="bg-[#0a0a0a] px-4 py-3">
            <p class="mono text-[0.62rem] uppercase tracking-[0.14em] text-zinc-500">{metric.label}</p>
            <p class="mt-1 text-lg font-medium tracking-[-0.03em] text-zinc-100">{metric.value}</p>
          </div>
        {/each}
      </div>
    </header>

    {#if viewState === 'loading'}
      <section class="grid gap-3 lg:grid-cols-[31rem_1fr]">
        <div class="min-h-[34rem] space-y-2 rounded-xl border border-white/10 bg-[#070707] p-3">
          {#each Array.from({ length: 7 }) as _, index (index)}
            <div class="h-12 animate-pulse rounded-md bg-white/10" style={`animation-delay: ${index * 70}ms`}></div>
          {/each}
        </div>
        <div class="h-[34rem] animate-pulse rounded-xl border border-white/10 bg-white/8"></div>
      </section>
    {:else if viewState === 'error'}
      <section class="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-100">
        <p class="text-sm font-medium">Assessment unavailable</p>
        <p class="mt-2 max-w-3xl text-sm leading-6">{errorMessage}</p>
      </section>
    {:else}
      <section class="grid gap-3 lg:grid-cols-[31rem_1fr]">
        <aside class="h-[calc(100dvh-13.5rem)] min-h-[34rem] overflow-hidden rounded-xl border border-white/10 bg-[#070707]/95 shadow-xl shadow-black/10">
          <div class="flex h-12 items-center justify-between border-b border-white/10 px-4">
            <h2 class="text-sm font-medium text-zinc-100">Issue queue</h2>
            <p class="text-xs text-zinc-500">Highest risk first</p>
          </div>

          <div class="grid h-9 grid-cols-[5.75rem_1fr_4.5rem] items-center border-b border-white/10 bg-white/[0.025] px-4 text-[0.68rem] uppercase tracking-[0.14em] text-zinc-500">
            <span>Severity</span>
            <span>Resource</span>
            <span class="text-right">Signals</span>
          </div>

          <div class="h-[calc(100%-5.25rem)] overflow-y-auto">
            {#each activeIncidents as incident, index (incident.title)}
              <button class="group grid w-full grid-cols-[0.2rem_1fr] border-b border-white/8 text-left last:border-b-0" onclick={() => selectIncident(index)}>
                <span class={[severityRail(incident.severity), selectedIncidentIndex === index ? 'opacity-100' : 'opacity-35']}></span>
                <span class={['grid grid-cols-[5.1rem_1fr_4.25rem] gap-3 px-4 py-3 transition', selectedIncidentIndex === index ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]']}>
                  <span class={`mono h-fit w-fit border px-1.5 py-0.5 text-[0.58rem] uppercase tracking-[0.12em] ${severityClasses(incident.severity)}`}>{incident.severity}</span>
                  <span class="min-w-0">
                    <span class="block truncate text-sm font-medium leading-5 text-zinc-100">{readableTitle(incident)}</span>
                    <span class="mt-1 line-clamp-2 block text-xs leading-5 text-zinc-400">{readableCause(incident)}</span>
                  </span>
                  <span class="text-right text-xs text-zinc-500">{incident.evidence.length}</span>
                </span>
              </button>
            {/each}
          </div>
        </aside>

        <section class="relative h-[calc(100dvh-13.5rem)] min-h-[34rem] min-w-0 overflow-hidden rounded-xl border border-white/10 bg-[#0b0b0b] shadow-xl shadow-black/10">
          {#if isRefreshing}
            <div class="pointer-events-none absolute inset-x-0 top-0 h-px overflow-hidden bg-white/10">
              <div class="h-full w-1/3 animate-pulse bg-white/60"></div>
            </div>
          {/if}
          {#if selectedIncident}
            <div class="min-h-[12rem] border-b border-white/10 p-4">
              <div class="grid gap-3 xl:grid-cols-[minmax(0,1fr)_22rem] xl:items-start">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class={`mono border px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.14em] ${severityClasses(selectedIncident.severity)}`}>{selectedIncident.severity}</span>
                    <span class="text-xs text-zinc-500">{selectedEvidence.length} evidence signals</span>
                  </div>
                  <h2 class="mt-2 line-clamp-3 text-2xl font-medium leading-8 tracking-[-0.035em] text-zinc-100">{selectedTitle}</h2>
                  <p class="mt-2 line-clamp-2 max-w-3xl text-sm leading-6 text-zinc-400">{selectedCause}</p>
                </div>

                <div class="min-h-[9rem] rounded-md border border-white/20 bg-white/[0.06] p-3">
                  <p class="text-sm font-medium text-zinc-100">Recommended check</p>
                  <pre class="mono mt-2 overflow-x-auto whitespace-pre-wrap text-[0.72rem] leading-5 text-zinc-100">{commandPreview}</pre>
                  <button class="mt-3 rounded-md border border-white/20 px-2.5 py-1.5 text-xs text-zinc-100 hover:bg-white/10" onclick={copyCommand}>
                    {commandCopied ? 'Copied' : 'Copy command'}
                  </button>
                </div>
              </div>
            </div>

            <div class="grid h-[calc(100%-12rem)] grid-rows-[auto_1fr_auto] p-4">
              <div class="mb-3 flex items-center justify-between gap-3">
                <h3 class="text-sm font-medium text-zinc-100">Evidence detail pane</h3>
                <p class="text-xs text-zinc-500">Read-only signals</p>
              </div>

              <div class="min-h-0 overflow-y-auto rounded-md border border-white/10">
                {#each selectedEvidence as evidence (`${evidence.source}-${evidence.signal}-${evidence.detail}`)}
                  <article class="grid gap-3 border-b border-white/8 bg-[#070707] p-3 last:border-b-0 md:grid-cols-[12rem_1fr]">
                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="mono text-[0.66rem] uppercase tracking-[0.14em] text-zinc-300">{evidence.source}</span>
                        <span class="mono rounded border border-white/15 bg-white/8 px-1.5 py-0.5 text-[0.58rem] uppercase tracking-[0.1em] text-zinc-300">{evidence.signal}</span>
                      </div>
                      <p class="mono mt-2 break-all text-[0.66rem] leading-4 text-zinc-600">{evidence.resource}</p>
                    </div>
                    <p class="text-sm leading-6 text-zinc-300">{readableEvidence(evidence.detail)}</p>
                  </article>
                {/each}
              </div>

              <div class="mt-3 flex h-7 items-center gap-3 border-t border-white/10 pt-3 text-xs text-zinc-500">
                <span>Connected to local emulator</span>
                <span class="text-zinc-700">|</span>
                <span>{liveSource}</span>
              </div>
            </div>
          {/if}
        </section>
      </section>
    {/if}
  </section>
</main>
