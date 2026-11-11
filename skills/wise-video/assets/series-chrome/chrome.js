/* Set text safely; the header is never animated or hidden by renderAt(). */
window.setSeriesChrome = function({episode, topic} = {}) {
 if (episode !== undefined) { const n=String(episode).replace(/^0+/, '') || '0'; document.querySelector('[data-episode-number]').textContent=n.padStart(2,'0'); document.querySelector('[data-series-name]').textContent=`纳斯达克投资 · 第${n}期`; }
 if (topic !== undefined) document.querySelector('[data-episode-topic]').textContent=String(topic);
};
