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
  const topLine = $derived(
    activeIncidents.length === 0
      ? 'Cluster is quiet.'
      : `${activeIncidents.length} active issue${activeIncidents.length === 1 ? '' : 's'} found in ${liveSource}.`
  );
  const metrics = $derived([
    { label: 'urgent', value: highSeverityCount.toString() },
    { label: 'affected', value: affectedResourceCount.toString() },
    { label: 'signals', value: assessment.evidence_count.toString() }
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
      return 'checkout-api is missing STRIPE_API_KEY';
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
      return 'The pod exits as soon as it starts because the deployment does not provide the Stripe API key environment variable.';
    }
    if (incident.likely_cause.includes('minimum availability')) {
      return 'The deployment is not meeting its availability target. Check the newest pod failures before rolling forward.';
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
      critical: 'border-red-500/70 bg-red-500/15 text-red-100',
      high: 'border-[#c9912b]/70 bg-[#c9912b]/12 text-[#f2d18d]',
      medium: 'border-[#5aa8b5]/60 bg-[#5aa8b5]/10 text-[#abd6dd]',
      low: 'border-slate-500/40 bg-slate-500/10 text-slate-300',
      info: 'border-slate-600/40 bg-slate-700/15 text-slate-400'
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

<main class="min-h-[100dvh] bg-[#080b10] px-4 py-5 text-slate-200 sm:px-6">
  <section class="mx-auto grid max-w-[1400px] gap-5">
    <header class="rounded-3xl border border-slate-500/15 bg-[#0b1017]/80 p-5 shadow-2xl shadow-black/20 sm:p-6">
      <div class="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div class="min-w-0">
          <p class="mono text-[0.68rem] uppercase tracking-[0.28em] text-[#5aa8b5]">Cluster issues</p>
          <h1 class="mt-3 max-w-4xl text-4xl font-semibold leading-[0.98] tracking-[-0.055em] text-slate-100 sm:text-5xl">
            {selectedTitle}
          </h1>
          <p class="mt-4 max-w-3xl text-base leading-7 text-slate-400">{selectedCause}</p>
        </div>

        <div class="flex shrink-0 flex-col gap-3 lg:items-end">
          <div class="mono max-w-[32rem] truncate text-xs text-slate-500">{topLine}</div>
          <div class="flex items-center gap-2">
            <span class={`mono border px-2.5 py-1 text-[0.68rem] uppercase tracking-[0.18em] ${severityClasses(assessment.severity)}`}>
              {assessment.severity}
            </span>
            <button class="rounded-lg border border-slate-500/20 bg-white/[0.03] px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.06]" onclick={refreshAssessment}>
              Refresh
            </button>
          </div>
        </div>
      </div>
    </header>

    {#if viewState === 'loading'}
      <section class="grid gap-5 lg:grid-cols-[0.56fr_1.44fr]">
        <div class="space-y-2 rounded-2xl border border-slate-500/15 bg-[#0d1219] p-3">
          {#each Array.from({ length: 5 }) as _, index (index)}
            <div class="h-20 animate-pulse rounded-xl bg-slate-700/20" style={`animation-delay: ${index * 70}ms`}></div>
          {/each}
        </div>
        <div class="h-[30rem] animate-pulse rounded-2xl border border-slate-500/15 bg-slate-700/15"></div>
      </section>
    {:else if viewState === 'error'}
      <section class="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-red-100">
        <p class="mono text-xs uppercase tracking-[0.24em]">Assessment unavailable</p>
        <p class="mt-4 max-w-3xl text-xl leading-7">{errorMessage}</p>
      </section>
    {:else}
      <section class="grid gap-5 lg:grid-cols-[0.56fr_1.44fr]">
        <aside class="rounded-2xl border border-slate-500/15 bg-[#0b1017]/95 p-4 shadow-2xl shadow-black/20">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-lg font-semibold tracking-[-0.03em] text-slate-100">Queue</h2>
            <p class="text-sm text-slate-500">Highest risk first</p>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-2">
            {#each metrics as metric (metric.label)}
              <div class="rounded-xl border border-slate-500/15 bg-[#0d1219] p-3">
                <p class="mono text-[0.62rem] uppercase tracking-[0.14em] text-slate-500">{metric.label}</p>
                <p class="mono mt-2 text-2xl text-slate-100">{metric.value}</p>
              </div>
            {/each}
          </div>

          <div class="mt-4 overflow-hidden rounded-xl border border-slate-500/15">
            {#each activeIncidents as incident, index (incident.title)}
              <button class="group grid w-full grid-cols-[0.25rem_1fr] border-b border-slate-500/15 text-left last:border-b-0" onclick={() => selectIncident(index)}>
                <span class={[severityRail(incident.severity), selectedIncidentIndex === index ? 'opacity-100' : 'opacity-40']}></span>
                <span class={['block px-4 py-4 transition', selectedIncidentIndex === index ? 'bg-white/[0.06]' : 'bg-[#0d1219] hover:bg-white/[0.035]']}>
                  <span class="flex flex-wrap items-center justify-between gap-3">
                    <span class={`mono border px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.16em] ${severityClasses(incident.severity)}`}>{incident.severity}</span>
                    <span class="text-xs text-slate-500">{incident.evidence.length} signals</span>
                  </span>
                  <span class="mt-3 block text-base font-medium tracking-[-0.025em] text-slate-100">{readableTitle(incident)}</span>
                  <span class="mt-2 line-clamp-2 block text-sm leading-5 text-slate-400">{readableCause(incident)}</span>
                </span>
              </button>
            {/each}
          </div>
        </aside>

        <section class="min-w-0 overflow-hidden rounded-2xl border border-slate-500/15 bg-[#101722] shadow-2xl shadow-black/20">
          {#if selectedIncident}
            <div class="border-b border-slate-500/15 bg-[#0b1017] p-5 sm:p-6">
              <div class="grid gap-4 xl:grid-cols-[1fr_auto] xl:items-end">
                <div>
                  <p class="text-sm font-medium text-slate-200">First check</p>
                  <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                    Confirm the failing pod before changing cluster state. The assistant stays read-only until an operator chooses the fix.
                  </p>
                </div>
                <div class="rounded-xl border border-[#c9912b]/25 bg-[#c9912b]/8 p-3 xl:w-[31rem]">
                  <pre class="mono overflow-x-auto whitespace-pre-wrap text-[0.74rem] leading-5 text-[#f2d18d]">{commandPreview}</pre>
                  <button class="mt-3 rounded-lg border border-[#c9912b]/25 px-3 py-2 text-sm text-[#f2d18d] hover:bg-[#c9912b]/10" onclick={copyCommand}>
                    {commandCopied ? 'Copied' : 'Copy command'}
                  </button>
                </div>
              </div>
            </div>

            <div class="p-5 sm:p-6">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-slate-200">Evidence</p>
                <p class="text-sm text-slate-500">{selectedEvidence.length} signals</p>
              </div>

              <div class="mt-4 divide-y divide-slate-500/15 overflow-hidden rounded-xl border border-slate-500/15">
                {#each selectedEvidence as evidence (`${evidence.source}-${evidence.signal}-${evidence.detail}`)}
                  <article class="grid gap-3 bg-[#0b1017] p-4 md:grid-cols-[11rem_1fr]">
                    <div>
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="mono text-[0.68rem] uppercase tracking-[0.16em] text-[#5aa8b5]">{evidence.source}</span>
                        <span class="mono rounded border border-slate-500/20 bg-slate-500/10 px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.12em] text-slate-300">{evidence.signal}</span>
                      </div>
                      <p class="mono mt-3 break-all text-[0.68rem] leading-4 text-slate-600">{evidence.resource}</p>
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
