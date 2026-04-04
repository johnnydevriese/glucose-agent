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

	$: fastingChart = buildSeries(fastingReadings, '#3b7f6b');
	$: prandialChart = buildSeries(prandialReadings, '#b85243');

	function formatDate(dateStr) {
		try {
			return format(new Date(dateStr), 'MMM d, yyyy');
		} catch {
			return dateStr;
		}
	}

	function buildSeries(series, color) {
		if (!series.length) {
			return { path: '', points: [], min: 0, max: 0, color };
		}

		const values = series.map((reading) => reading.glucose_level);
		const min = Math.min(...values);
		const max = Math.max(...values);
		const range = Math.max(max - min, 1);
		const width = 100;
		const height = 100;

		const points = series.map((reading, index) => {
			const x = series.length === 1 ? width / 2 : (index / (series.length - 1)) * width;
			const y = height - ((reading.glucose_level - min) / range) * height;
			return {
				x,
				y,
				label: formatDate(reading.date),
				value: reading.glucose_level
			};
		});

		return {
			path: points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' '),
			points,
			min,
			max,
			color
		};
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
			<div class="mb-5 grid gap-5 lg:grid-cols-2">
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

			<div class="grid gap-5 lg:grid-cols-2">
				<div class="soft-panel rounded-[1.5rem] p-5">
					<div class="mb-4 flex items-end justify-between gap-4">
						<div>
							<p class="metric-label">Fasting trend</p>
							<p class="mt-2 text-sm leading-7 text-[var(--ink-soft)]">
								A quick look at how fasting readings have moved across your recent entries.
							</p>
						</div>
						{#if fastingReadings.length}
							<div class="text-right text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">
								<div>Range</div>
								<div class="mt-1 font-semibold text-[var(--ink-strong)]">
									{fastingChart.min} to {fastingChart.max}
								</div>
							</div>
						{/if}
					</div>
					{#if fastingReadings.length}
						<svg viewBox="0 0 100 100" class="h-44 w-full overflow-visible">
							<line x1="0" y1="100" x2="100" y2="100" stroke="rgba(125,84,76,0.18)" stroke-width="1" />
							<path
								d={fastingChart.path}
								fill="none"
								stroke={fastingChart.color}
								stroke-width="3"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
							{#each fastingChart.points as point}
								<circle cx={point.x} cy={point.y} r="3.2" fill={fastingChart.color}>
									<title>{point.label}: {point.value} mg/dL</title>
								</circle>
							{/each}
						</svg>
					{:else}
						<p class="text-sm leading-7 text-[var(--ink-soft)]">No fasting readings yet.</p>
					{/if}
				</div>

				<div class="soft-panel rounded-[1.5rem] p-5">
					<div class="mb-4 flex items-end justify-between gap-4">
						<div>
							<p class="metric-label">After-meal trend</p>
							<p class="mt-2 text-sm leading-7 text-[var(--ink-soft)]">
								Recent post-meal values, useful for spotting meal-driven swings.
							</p>
						</div>
						{#if prandialReadings.length}
							<div class="text-right text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">
								<div>Range</div>
								<div class="mt-1 font-semibold text-[var(--ink-strong)]">
									{prandialChart.min} to {prandialChart.max}
								</div>
							</div>
						{/if}
					</div>
					{#if prandialReadings.length}
						<svg viewBox="0 0 100 100" class="h-44 w-full overflow-visible">
							<line x1="0" y1="100" x2="100" y2="100" stroke="rgba(125,84,76,0.18)" stroke-width="1" />
							<path
								d={prandialChart.path}
								fill="none"
								stroke={prandialChart.color}
								stroke-width="3"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
							{#each prandialChart.points as point}
								<circle cx={point.x} cy={point.y} r="3.2" fill={prandialChart.color}>
									<title>{point.label}: {point.value} mg/dL</title>
								</circle>
							{/each}
						</svg>
					{:else}
						<p class="text-sm leading-7 text-[var(--ink-soft)]">No after-meal readings yet.</p>
					{/if}
				</div>
			</div>
		{/if}
	</section>
</div>
