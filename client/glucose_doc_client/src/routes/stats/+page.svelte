<script>
	// @ts-nocheck
	import { onMount } from 'svelte';
	import { websocketStore, stats, readings, connected } from '$lib/stores/websocket';
	import { format } from 'date-fns';

	onMount(() => {
		if (!$connected) {
			websocketStore.connect();
		}
		// Request stats data when component mounts
		websocketStore.getStats();
	});

	// Calculate additional stats
	$: fastingReadings = $readings.filter((r) => r.meal_status === 'fasting');
	$: prandialReadings = $readings.filter((r) => r.meal_status === 'prandial');

	// Get latest readings
	$: latestFasting =
		fastingReadings.length > 0 ? fastingReadings[fastingReadings.length - 1] : null;

	$: latestPrandial =
		prandialReadings.length > 0 ? prandialReadings[prandialReadings.length - 1] : null;

	function formatDate(dateStr) {
		try {
			return format(new Date(dateStr), 'MMM d, yyyy');
		} catch {
			return dateStr;
		}
	}
</script>

<div class="space-y-6">
	<section class="glass-panel-strong rounded-[2rem] p-6 sm:p-8">
		<p class="section-eyebrow mb-2">Trend overview</p>
		<div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
			<div>
				<h2 class="font-[var(--font-display)] text-4xl tracking-[-0.04em] text-[var(--ink-strong)]">
					Stats that read like a briefing, not a billing dashboard.
				</h2>
				<p class="mt-3 max-w-2xl text-sm leading-7 text-[var(--ink-soft)]">
					Quick visibility into your current averages, latest readings, and the usual target
					ranges for fasting and after-meal checks.
				</p>
			</div>
		</div>
	</section>

	<div class="grid gap-5 md:grid-cols-3">
		<div class="metric-card">
			<p class="metric-label">Total readings</p>
			<p class="metric-value mt-3">{$stats.total_readings}</p>
		</div>
		<div class="metric-card">
			<p class="metric-label">Fasting entries</p>
			<p class="metric-value mt-3">{fastingReadings.length}</p>
		</div>
		<div class="metric-card">
			<p class="metric-label">After-meal entries</p>
			<p class="metric-value mt-3">{prandialReadings.length}</p>
		</div>
	</div>

	<section class="glass-panel-strong rounded-[2rem] p-6 sm:p-8">
		{#if !$connected}
			<div class="rounded-2xl border border-[rgba(176,114,45,0.18)] bg-[rgba(255,248,235,0.86)] p-4 text-sm text-[var(--warning)]">
				Connecting to server... Please wait.
			</div>
		{:else if $stats.total_readings === 0}
			<div class="py-8 text-center">
				<h3 class="font-[var(--font-display)] text-3xl tracking-[-0.03em] text-[var(--ink-strong)]">
					No statistics yet
				</h3>
				<p class="mx-auto mt-3 max-w-md text-sm leading-7 text-[var(--ink-soft)]">
					Record a few readings and this space will turn into a much more useful summary of
					your rhythm.
				</p>
				<div class="mt-6">
					<a href="/" class="btn btn-primary">Record a Reading</a>
				</div>
			</div>
		{:else}
			<div class="grid gap-5 lg:grid-cols-2">
				<div class="soft-panel rounded-[1.5rem] p-5">
					<p class="metric-label">Average fasting</p>
					<p class="mt-3 font-[var(--font-display)] text-4xl tracking-[-0.04em]">
						{$stats.avg_fasting ?? '–'} <span class="text-lg">mg/dL</span>
					</p>
					<p class="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
						Best compared against a typical fasting target of roughly 70-100 mg/dL.
					</p>
				</div>
				<div class="soft-panel rounded-[1.5rem] p-5">
					<p class="metric-label">Average after meal</p>
					<p class="mt-3 font-[var(--font-display)] text-4xl tracking-[-0.04em]">
						{$stats.avg_prandial ?? '–'} <span class="text-lg">mg/dL</span>
					</p>
					<p class="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
						Many after-meal checks aim to stay under about 140 mg/dL two hours after eating.
					</p>
				</div>
				<div class="soft-panel rounded-[1.5rem] p-5">
					<p class="metric-label">Latest fasting</p>
					{#if latestFasting}
						<p class="mt-3 font-[var(--font-display)] text-4xl tracking-[-0.04em]">
							{latestFasting.glucose_level} <span class="text-lg">mg/dL</span>
						</p>
						<p class="mt-3 text-sm text-[var(--ink-soft)]">{formatDate(latestFasting.date)}</p>
					{:else}
						<p class="mt-3 text-sm leading-7 text-[var(--ink-soft)]">No fasting reading recorded yet.</p>
					{/if}
				</div>
				<div class="soft-panel rounded-[1.5rem] p-5">
					<p class="metric-label">Latest after meal</p>
					{#if latestPrandial}
						<p class="mt-3 font-[var(--font-display)] text-4xl tracking-[-0.04em]">
							{latestPrandial.glucose_level} <span class="text-lg">mg/dL</span>
						</p>
						<p class="mt-3 text-sm text-[var(--ink-soft)]">{formatDate(latestPrandial.date)}</p>
					{:else}
						<p class="mt-3 text-sm leading-7 text-[var(--ink-soft)]">No after-meal reading recorded yet.</p>
					{/if}
				</div>
			</div>
		{/if}
	</section>
</div>
