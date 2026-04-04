<script>
	// @ts-nocheck
	import { onMount } from 'svelte';
	import { websocketStore, messages, extractedReading, connected } from '$lib/stores/websocket';
	import { fly } from 'svelte/transition';

	let messageInput = '';
	let notesInput = '';
	let messagesContainer;
	const prompts = [
		'My blood sugar was 118 today fasting',
		'I was 142 yesterday after breakfast',
		"What is a normal fasting glucose range?"
	];

	// Scroll to bottom when messages update
	function scrollToBottom() {
		if (messagesContainer) {
			setTimeout(() => {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}, 50); // Slight delay to ensure DOM is updated
		}
	}

	$: if ($messages && $messages.length) {
		scrollToBottom();
	}

	// Also scroll after animations complete
	onMount(() => {
		// Initial scroll to bottom
		scrollToBottom();
	});

	function handleSendMessage() {
		if (messageInput.trim()) {
			websocketStore.sendMessage(messageInput.trim());
			messageInput = '';
		}
	}

	function handleConfirmReading() {
		if ($extractedReading) {
			websocketStore.confirmReading($extractedReading, notesInput);
			notesInput = '';
		}
	}

	function handleCancelConfirmation() {
		websocketStore.dismissExtractedReading();
	}

	function handleKeyPress(event) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSendMessage();
		}
	}

	onMount(() => {
		if (!$connected) {
			websocketStore.connect();
		}
	});

	function usePrompt(prompt) {
		messageInput = prompt;
	}
</script>

<div class="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
	<section class="glass-panel-strong overflow-hidden rounded-[2rem]">
		<div class="sticky top-24 z-10 border-b border-[rgba(125,84,76,0.12)] bg-[rgba(255,250,244,0.92)] p-5 backdrop-blur-xl sm:p-7">
			<div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
				<div>
					<p class="section-eyebrow mb-2">Chat Studio</p>
					<h2 class="font-[var(--font-display)] text-3xl tracking-[-0.04em] text-[var(--ink-strong)] sm:text-4xl">
						Talk like a person. Capture like a product.
					</h2>
					<p class="mt-3 max-w-2xl text-sm leading-7 text-[var(--ink-soft)]">
						Describe your reading naturally and Glucose Buddy will extract the number, date,
						and meal context for confirmation.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<span
						class="status-chip {$connected ? 'status-chip-success' : 'status-chip-warning'}"
					>
						<span class="h-2 w-2 rounded-full bg-current"></span>
						{$connected ? 'Live connection' : 'Connecting'}
					</span>
				</div>
			</div>
			<div class="mt-4 flex flex-wrap gap-2">
				<div class="rounded-full border border-[rgba(125,84,76,0.14)] bg-white/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
					Natural language logging
				</div>
				<div class="rounded-full border border-[rgba(125,84,76,0.14)] bg-white/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
					Deterministic validation
				</div>
				<div class="rounded-full border border-[rgba(125,84,76,0.14)] bg-white/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
					Agent-assisted UX
				</div>
			</div>
		</div>

		<div
			class="flex h-[34rem] flex-col overflow-y-auto bg-[linear-gradient(180deg,rgba(255,252,247,0.64),rgba(248,231,223,0.2))] p-4 sm:p-6"
			bind:this={messagesContainer}
		>
			{#each $messages as message, i}
				<div
					class="{message.fromUser ? 'self-end' : 'self-start'} mb-4 max-w-[85%] sm:max-w-[75%]"
					in:fly={{ y: 16, duration: 180 }}
					on:introend={scrollToBottom}
				>
					<div class="mb-1 px-1 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
						{message.fromUser ? 'You' : 'Glucose Buddy'}
					</div>
					<div
						class="inline-block rounded-[1.4rem] px-4 py-3 text-sm leading-7 sm:px-5 {message.fromUser
							? 'message-bubble-user'
							: 'message-bubble-agent'}"
					>
						<p class="whitespace-pre-wrap">{message.content}</p>
					</div>
				</div>
			{/each}

			{#if !$connected}
				<div class="self-start rounded-2xl border border-[rgba(176,114,45,0.18)] bg-[rgba(255,248,235,0.86)] p-4 text-sm text-[var(--warning)]">
					Connecting to server... Please wait.
				</div>
			{/if}
		</div>

		{#if $extractedReading}
			<div class="border-y border-[rgba(125,84,76,0.12)] bg-[rgba(255,244,239,0.72)] p-5 sm:p-6">
				<div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
					<div>
						<p class="section-eyebrow mb-1">Pending confirmation</p>
						<h3 class="font-[var(--font-display)] text-3xl tracking-[-0.03em] text-[var(--ink-strong)]">
							Confirm this reading
						</h3>
					</div>
					<span class="status-chip status-chip-success">Ready to save</span>
				</div>

				<div class="soft-panel mb-4 rounded-[1.5rem] p-4 sm:p-5">
					<div class="grid gap-4 sm:grid-cols-3">
						<div>
							<span class="metric-label">Glucose level</span>
							<p class="mt-2 font-[var(--font-display)] text-3xl tracking-[-0.04em]">
								{$extractedReading.glucose_level} <span class="text-lg">mg/dL</span>
							</p>
						</div>
						<div>
							<span class="metric-label">Date</span>
							<p class="mt-2 text-lg font-semibold text-[var(--ink-strong)]">
								{$extractedReading.date}
							</p>
						</div>
						<div>
							<span class="metric-label">Meal status</span>
							<p class="mt-2 text-lg font-semibold capitalize text-[var(--ink-strong)]">
								{$extractedReading.meal_status}
							</p>
						</div>
					</div>
				</div>

				<div class="mb-4">
					<label for="notes" class="label">Additional Notes (optional)</label>
					<textarea
						id="notes"
						bind:value={notesInput}
						class="textarea h-28 resize-none"
						placeholder="Exercise, stress, meal size, medication timing, or anything worth remembering..."
					></textarea>
				</div>

				<div class="flex flex-wrap gap-3">
					<button class="btn btn-primary" on:click={handleConfirmReading}>Confirm</button>
					<button class="btn btn-secondary" on:click={handleCancelConfirmation}>Dismiss</button>
				</div>
			</div>
		{/if}

		{#if !$extractedReading}
			<div class="border-t border-[rgba(125,84,76,0.12)] p-4 sm:p-6">
				<div class="flex flex-col gap-3 sm:flex-row">
					<input
						type="text"
						placeholder="Share your blood sugar reading or ask a question..."
						class="input flex-1"
						bind:value={messageInput}
						on:keypress={handleKeyPress}
						disabled={!$connected}
					/>
					<button
						class="btn btn-primary whitespace-nowrap"
						on:click={handleSendMessage}
						disabled={!$connected || !messageInput.trim()}
					>
						Send
					</button>
				</div>
				<div class="mt-4">
					<p class="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
						Try a prompt
					</p>
					<div class="flex flex-wrap gap-2">
						{#each prompts as prompt}
							<button class="btn btn-secondary !px-4 !py-3 text-sm" on:click={() => usePrompt(prompt)}>
								{prompt}
							</button>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</section>

	<aside class="flex flex-col gap-6">
		<div class="glass-panel rounded-[2rem] p-5 sm:p-6">
			<p class="section-eyebrow mb-2">Workflow</p>
			<h3 class="font-[var(--font-display)] text-3xl tracking-[-0.03em]">Fast, careful, readable.</h3>
			<div class="mt-5 space-y-4 text-sm leading-7 text-[var(--ink-soft)]">
				<div>
					<p class="font-semibold text-[var(--ink-strong)]">1. Say it naturally</p>
					<p>Use everyday language instead of filling out forms.</p>
				</div>
				<div>
					<p class="font-semibold text-[var(--ink-strong)]">2. Confirm what matters</p>
					<p>Only the extracted reading asks for review before it is stored.</p>
				</div>
				<div>
					<p class="font-semibold text-[var(--ink-strong)]">3. Track the pattern</p>
					<p>History and insights stay one click away with the same calm visual language.</p>
				</div>
			</div>
		</div>

		<div class="metric-card">
			<p class="metric-label">Good examples</p>
			<ul class="mt-4 space-y-3 text-sm leading-7 text-[var(--ink-soft)]">
				<li>"112 this morning fasting"</li>
				<li>"I was 146 after dinner yesterday"</li>
				<li>"Compare my recent fasting readings"</li>
			</ul>
		</div>
	</aside>
</div>
