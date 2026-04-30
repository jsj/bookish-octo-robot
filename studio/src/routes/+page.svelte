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
    { label: 'Issues', value: activeIncidents.length.toString() },
    { label: 'Urgent', value: highSeverityCount.toString() },
    { label: 'Affected', value: affectedResourceCount.toString() },
    { label: 'Signals', value: assessment.evidence_count.toString() }
  ]);

  onMount(() => {
    void refreshAssessment();
  });

  async function refreshAssessment() {
    viewState = 'loading';
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
      viewState = 'ready';
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Unable to load assessment';
      viewState = 'error';
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
      critical: 'border-red-500/60 bg-red-500/10 text-red-100',
      high: 'border-[#c9912b]/60 bg-[#c9912b]/10 text-[#f2d18d]',
      medium: 'border-[#5aa8b5]/50 bg-[#5aa8b5]/8 text-[#abd6dd]',
      low: 'border-slate-500/35 bg-slate-500/8 text-slate-300',
      info: 'border-slate-600/35 bg-slate-700/12 text-slate-400'
    }[severity];
  }

  function severityRail(severity: Severity) {
    return {
      critical: 'bg-red-500',
      high: 'bg-[#c9912b]',
      medium: 'bg-[#5aa8b5]',
      low: 'bg-slate-500',
      info: 'bg-slate-600'
    }[severity];
  }
</script>

<svelte:head>
  <title>Cluster Triage</title>
  <meta name="description" content="Kubernetes incident triage for local SRE assessment." />
</svelte:head>

<main class="min-h-[100dvh] bg-[#080b10] px-4 py-6 text-slate-200 sm:px-6">
  <section class="mx-auto grid max-w-[1280px] gap-4">
    <header class="rounded-xl border border-slate-500/15 bg-[#0b1017]/90 p-4 shadow-xl shadow-black/10">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="min-w-0">
          <h1 class="text-xl font-medium tracking-[-0.025em] text-slate-100">Cluster triage</h1>
          <p class="mt-1 text-sm leading-6 text-slate-400">
            {activeIncidents.length} active issue{activeIncidents.length === 1 ? '' : 's'} from {liveSource}
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          {#each metrics as metric (metric.label)}
            <div class="rounded-md border border-slate-500/15 bg-[#0d1219] px-3 py-2">
              <span class="mono text-[0.62rem] uppercase tracking-[0.14em] text-slate-500">{metric.label}</span>
              <span class="mono ml-2 text-sm text-slate-100">{metric.value}</span>
            </div>
          {/each}
          <span class={`mono border px-2.5 py-1.5 text-[0.68rem] uppercase tracking-[0.16em] ${severityClasses(assessment.severity)}`}>
            {assessment.severity}
          </span>
          <button class="rounded-md border border-slate-500/20 bg-white/[0.03] px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.06]" onclick={refreshAssessment}>
            Refresh
          </button>
        </div>
      </div>
    </header>

    {#if viewState === 'loading'}
      <section class="grid gap-4 lg:grid-cols-[24rem_1fr]">
        <div class="space-y-2 rounded-xl border border-slate-500/15 bg-[#0b1017] p-3">
          {#each Array.from({ length: 5 }) as _, index (index)}
            <div class="h-[4.75rem] animate-pulse rounded-md bg-slate-700/20" style={`animation-delay: ${index * 70}ms`}></div>
          {/each}
        </div>
        <div class="h-[34rem] animate-pulse rounded-xl border border-slate-500/15 bg-slate-700/15"></div>
      </section>
    {:else if viewState === 'error'}
      <section class="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-100">
        <p class="text-sm font-medium">Assessment unavailable</p>
        <p class="mt-2 max-w-3xl text-sm leading-6">{errorMessage}</p>
      </section>
    {:else}
      <section class="grid gap-4 lg:grid-cols-[24rem_1fr]">
        <aside class="rounded-xl border border-slate-500/15 bg-[#0b1017]/95 shadow-xl shadow-black/10">
          <div class="flex h-12 items-center justify-between border-b border-slate-500/15 px-4">
            <h2 class="text-sm font-medium text-slate-100">Queue</h2>
            <p class="text-xs text-slate-500">Highest risk first</p>
          </div>

          <div class="max-h-[calc(100dvh-12rem)] overflow-y-auto">
            {#each activeIncidents as incident, index (incident.title)}
              <button class="group grid w-full grid-cols-[0.2rem_1fr] border-b border-slate-500/12 text-left last:border-b-0" onclick={() => selectIncident(index)}>
                <span class={[severityRail(incident.severity), selectedIncidentIndex === index ? 'opacity-100' : 'opacity-35']}></span>
                <span class={['block px-4 py-3 transition', selectedIncidentIndex === index ? 'bg-white/[0.055]' : 'hover:bg-white/[0.03]']}>
                  <span class="flex items-center justify-between gap-3">
                    <span class="text-sm font-medium leading-5 text-slate-100">{readableTitle(incident)}</span>
                    <span class={`mono shrink-0 border px-1.5 py-0.5 text-[0.58rem] uppercase tracking-[0.12em] ${severityClasses(incident.severity)}`}>{incident.severity}</span>
                  </span>
                  <span class="mt-1 line-clamp-2 block text-xs leading-5 text-slate-400">{readableCause(incident)}</span>
                  <span class="mt-2 block text-xs text-slate-500">{incident.evidence.length} signals</span>
                </span>
              </button>
            {/each}
          </div>
        </aside>

        <section class="min-w-0 rounded-xl border border-slate-500/15 bg-[#101722] shadow-xl shadow-black/10">
          {#if selectedIncident}
            <div class="border-b border-slate-500/15 p-4">
              <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class={`mono border px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.14em] ${severityClasses(selectedIncident.severity)}`}>{selectedIncident.severity}</span>
                    <span class="text-xs text-slate-500">{selectedEvidence.length} evidence signals</span>
                  </div>
                  <h2 class="mt-2 text-2xl font-medium leading-8 tracking-[-0.035em] text-slate-100">{selectedTitle}</h2>
                  <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{selectedCause}</p>
                </div>

                <div class="rounded-md border border-[#c9912b]/25 bg-[#c9912b]/8 p-3 xl:w-[28rem]">
                  <p class="text-sm font-medium text-[#f2d18d]">First check</p>
                  <pre class="mono mt-2 overflow-x-auto whitespace-pre-wrap text-[0.72rem] leading-5 text-[#f2d18d]">{commandPreview}</pre>
                  <button class="mt-3 rounded-md border border-[#c9912b]/25 px-2.5 py-1.5 text-xs text-[#f2d18d] hover:bg-[#c9912b]/10" onclick={copyCommand}>
                    {commandCopied ? 'Copied' : 'Copy command'}
                  </button>
                </div>
              </div>
            </div>

            <div class="p-4">
              <div class="mb-3 flex items-center justify-between gap-3">
                <h3 class="text-sm font-medium text-slate-100">Evidence</h3>
                <p class="text-xs text-slate-500">Read-only signals</p>
              </div>

              <div class="overflow-hidden rounded-md border border-slate-500/15">
                {#each selectedEvidence as evidence (`${evidence.source}-${evidence.signal}-${evidence.detail}`)}
                  <article class="grid gap-3 border-b border-slate-500/12 bg-[#0b1017] p-3 last:border-b-0 md:grid-cols-[12rem_1fr]">
                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="mono text-[0.66rem] uppercase tracking-[0.14em] text-[#5aa8b5]">{evidence.source}</span>
                        <span class="mono rounded border border-slate-500/20 bg-slate-500/10 px-1.5 py-0.5 text-[0.58rem] uppercase tracking-[0.1em] text-slate-300">{evidence.signal}</span>
                      </div>
                      <p class="mono mt-2 break-all text-[0.66rem] leading-4 text-slate-600">{evidence.resource}</p>
                    </div>
                    <p class="text-sm leading-6 text-slate-300">{readableEvidence(evidence.detail)}</p>
                  </article>
                {/each}
              </div>
            </div>
          {/if}
        </section>
      </section>
    {/if}
  </section>
</main>
