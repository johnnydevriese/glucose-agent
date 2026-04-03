<script>
	import '../app.css';
	import { page } from '$app/stores';
</script>

<div class="app-shell">
	<div class="mx-auto flex min-h-screen max-w-7xl flex-col px-4 pb-8 pt-5 sm:px-6 lg:px-8">
		<nav class="glass-panel-strong sticky top-4 z-20 rounded-[1.75rem] px-4 py-4 sm:px-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
				<div class="flex items-center gap-4">
					<div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-[rgba(184,82,67,0.14)] text-2xl">
						<span aria-hidden="true">🩸</span>
					</div>
					<div>
						<p class="section-eyebrow">Glucose Companion</p>
						<a href="/" class="font-[var(--font-display)] text-3xl tracking-[-0.04em] text-[var(--ink-strong)]">
							Glucose Buddy
						</a>
					</div>
				</div>
				<div class="flex flex-wrap gap-2">
					<a
						href="/"
						class="nav-pill"
						class:nav-pill-active={$page.url.pathname === '/'}
						aria-current={$page.url.pathname === '/' ? 'page' : undefined}
					>
						Chat Studio
					</a>
					<a
						href="/history"
						class="nav-pill"
						class:nav-pill-active={$page.url.pathname === '/history'}
						aria-current={$page.url.pathname === '/history' ? 'page' : undefined}
					>
						History
					</a>
					<a
						href="/stats"
						class="nav-pill"
						class:nav-pill-active={$page.url.pathname === '/stats'}
						aria-current={$page.url.pathname === '/stats' ? 'page' : undefined}
					>
						Insights
					</a>
				</div>
			</div>
		</nav>

		<header class="relative py-10 sm:py-14">
			<div class="ambient-grid absolute inset-x-0 top-8 -z-10 h-56 rounded-[2rem] opacity-50"></div>
			<div class="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
				<div class="max-w-3xl">
					<p class="section-eyebrow mb-3">Conversation-first tracking</p>
					<h1 class="hero-title">Beautiful glucose logging that still feels clinical and clear.</h1>
					<p class="hero-copy mt-5">
						Log readings naturally, confirm details quickly, and keep a calm view of your
						day-to-day patterns without the usual sterile dashboard feel.
					</p>
				</div>
				<div class="glass-panel rounded-[1.75rem] p-5 sm:min-w-[22rem]">
					<p class="section-eyebrow mb-2">What this app does</p>
					<p class="text-sm leading-7 text-[var(--ink-soft)]">
						Captures fasting and after-meal readings, keeps a running history, and turns the
						stream into usable feedback instead of just storing numbers.
					</p>
				</div>
			</div>
		</header>

		<main class="flex-1">
			<slot></slot>
		</main>

		<footer class="mt-14 border-t border-[rgba(125,84,76,0.14)] py-8">
			<p class="text-sm text-[var(--ink-soft)]">
				Designed for calm, high-signal tracking. Glucose Buddy helps with logging and education,
				not medical diagnosis or medication changes.
			</p>
		</footer>
	</div>
</div>
