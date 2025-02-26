<!-- src/routes/stats/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { websocketStore, stats, readings, connected } from '$lib/stores/websocket';

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
</script>

<div class="mx-auto max-w-4xl">
	<div class="overflow-hidden rounded-lg bg-white shadow">
		<div class="border-b p-4 sm:p-6">
			<h1 class="text-xl font-bold text-gray-900">Blood Sugar Statistics</h1>
			<p class="text-sm text-gray-500">Overview of your glucose readings</p>
		</div>

		<div class="p-4 sm:p-6">
			{#if !$connected}
				<div class="rounded-md bg-yellow-50 p-3 text-yellow-800">
					Connecting to server... Please wait.
				</div>
			{:else if $stats.total_readings === 0}
				<div class="p-6 text-center">
					<div
						class="bg-primary-100 mx-auto flex h-12 w-12 items-center justify-center rounded-full"
					>
						<svg
							class="text-primary-600 h-6 w-6"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							/>
						</svg>
					</div>
					<h3 class="mt-2 text-sm font-medium text-gray-900">No statistics available yet</h3>
					<p class="mt-1 text-sm text-gray-500">Record some readings to see your statistics.</p>
					<div class="mt-6">
						<a href="/" class="btn btn-primary"> Record a Reading </a>
					</div>
				</div>
			{:else}
				<!-- Summary Cards -->
				<div class="mb-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
					<!-- Total Readings -->
					<div class="overflow-hidden rounded-lg bg-white shadow">
						<div class="px-4 py-5 sm:p-6">
							<dt class="truncate text-sm font-medium text-gray-500">Total Readings</dt>
							<dd class="text-primary-700 mt-1 text-3xl font-semibold">
								{$stats.total_readings}
							</dd>
						</div>
					</div>

					<!-- Average Fasting -->
					{#if $stats.has_fasting && $stats.avg_fasting !== undefined}
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="px-4 py-5 sm:p-6">
								<dt class="truncate text-sm font-medium text-gray-500">Average Fasting</dt>
								<dd class="text-primary-700 mt-1 text-3xl font-semibold">
									{$stats.avg_fasting} mg/dL
								</dd>
							</div>
						</div>
					{/if}

					<!-- Average After Meal -->
					{#if $stats.has_prandial && $stats.avg_prandial !== undefined}
						<div class="overflow-hidden rounded-lg bg-white shadow">
							<div class="px-4 py-5 sm:p-6">
								<dt class="truncate text-sm font-medium text-gray-500">Average After Meal</dt>
								<dd class="text-primary-700 mt-1 text-3xl font-semibold">
									{$stats.avg_prandial} mg/dL
								</dd>
							</div>
						</div>
					{/if}
				</div>

				<!-- Latest Readings -->
				<h2 class="mb-4 text-lg font-medium text-gray-900">Latest Readings</h2>

				<div class="mb-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
					<!-- Latest Fasting -->
					<div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
						<div class="px-4 py-5 sm:p-6">
							<h3 class="text-lg font-medium leading-6 text-gray-900">Latest Fasting</h3>

							{#if latestFasting}
								<div class="mt-4">
									<div class="flex justify-between">
										<dt class="text-sm font-medium text-gray-500">Value</dt>
										<dd class="text-sm text-gray-900">{latestFasting.glucose_level} mg/dL</dd>
									</div>
									<div class="mt-2 flex justify-between">
										<dt class="text-sm font-medium text-gray-500">Date</dt>
										<dd class="text-sm text-gray-900">{latestFasting.date}</dd>
									</div>
								</div>
							{:else}
								<p class="mt-4 text-sm text-gray-500">No fasting readings yet</p>
							{/if}
						</div>
					</div>

					<!-- Latest After Meal -->
					<div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
						<div class="px-4 py-5 sm:p-6">
							<h3 class="text-lg font-medium leading-6 text-gray-900">Latest After Meal</h3>

							{#if latestPrandial}
								<div class="mt-4">
									<div class="flex justify-between">
										<dt class="text-sm font-medium text-gray-500">Value</dt>
										<dd class="text-sm text-gray-900">{latestPrandial.glucose_level} mg/dL</dd>
									</div>
									<div class="mt-2 flex justify-between">
										<dt class="text-sm font-medium text-gray-500">Date</dt>
										<dd class="text-sm text-gray-900">{latestPrandial.date}</dd>
									</div>
								</div>
							{:else}
								<p class="mt-4 text-sm text-gray-500">No after-meal readings yet</p>
							{/if}
						</div>
					</div>
				</div>

				<!-- Ranges Information -->
				<div class="rounded-lg border border-blue-200 bg-blue-50 p-4">
					<h3 class="mb-2 text-sm font-medium text-blue-800">Normal Blood Sugar Ranges</h3>
					<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
						<div class="rounded border border-blue-100 bg-white p-3">
							<p class="text-xs font-medium text-gray-500">Fasting</p>
							<p class="text-sm">70-100 mg/dL</p>
						</div>
						<div class="rounded border border-blue-100 bg-white p-3">
							<p class="text-xs font-medium text-gray-500">After Meals (2 hours)</p>
							<p class="text-sm">Less than 140 mg/dL</p>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
