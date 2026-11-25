#!/usr/bin/env node
// Renders the reusable transparent overlays into cards/overlays/. Re-run after editing layout.json or lib.cjs.
const L = require('./lib.cjs'); const O = L.V2 + '/cards/overlays';
(async () => {
  const ctx = await L.launch();
  const jobs = [];
  for (const k of ['sarvam', 'nudgebee', 'flagsmith', 'all']) jobs.push([`sponsor_${k}.png`, L.sponsorHtml(k), L.SPONSOR_CSS, true]);
  jobs.push(['caption_example.png', L.captionHtml('One tap. Then she just talks.'), L.captionCss(), true]);
  jobs.push(['subtitle_example_right.png', L.subtitleHtml('I need a time for darshan today, dear.'), L.subtitleCss('right'), true]);
  jobs.push(['subtitle_example_center.png', L.subtitleHtml('I am at River Crossing. My knees hurt.\\nIs there somewhere to sit?'), L.subtitleCss('center'), true]);
  jobs.push(['phone_back.png', L.phoneBackHtml(), '', false]);
  jobs.push(['phone_ring.png', L.phoneRingHtml(), '', true]);
  jobs.push(['split_mask.png', L.splitMaskHtml({}), L.SPLIT_CSS, true]);
  for (const [name, html, css, tr] of jobs) {
    const h = await L.openHtml(ctx, html, css); await L.shot(h.page, `${O}/${name}`, tr); await h.page.close(); L.cleanup(h);
  }
  await ctx.close(); console.log('overlays done:', jobs.map(j => j[0]).join(' '));
})();
