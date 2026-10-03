export default {
  async fetch(request, env) {
    // Only accept POST requests from Telegram
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // Security check: Validate Telegram Secret Token header
    const secretHeader = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (env.TELEGRAM_SECRET_TOKEN && secretHeader !== env.TELEGRAM_SECRET_TOKEN) {
      return new Response("Unauthorized", { status: 401 });
    }

    try {
      const updateData = await request.json();

      // Trigger GitHub repository_dispatch event
      const githubUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`;

      const response = await fetch(githubUrl, {
        method: "POST",
        headers: {
          "Accept": "application/vnd.github.v3+json",
          "Authorization": `Bearer ${env.GITHUB_PAT}`,
          "User-Agent": "Cloudflare-Worker-RemNewz-Proxy",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          event_type: "telegram-webhook",
          client_payload: {
            update: updateData
          }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        return new Response(`GitHub dispatch failed: ${errorText}`, { status: 500 });
      }

      // Return 200 OK to Telegram to confirm delivery
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
        status: 200
      });
    } catch (err) {
      return new Response(`Error: ${err.message}`, { status: 500 });
    }
  }
};
