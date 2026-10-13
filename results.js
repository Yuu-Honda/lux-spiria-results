// Select among recorded aggregates. No requests, storage, or engine execution.
'use strict';
const cutoff = document.querySelector('[data-chart-cutoff]');
if (cutoff) {
  cutoff.addEventListener('change', () => {
    const k = Number(cutoff.value);
    if (![1, 3, 5].includes(k)) return;
    document.querySelectorAll('.chart-row').forEach(row => {
      const count = Number(row.getAttribute(`data-at-${k}`));
      row.querySelector('.chart-value').textContent = `${count} / 22`;
      row.querySelector('.chart-fill').style.width = `${count / 22 * 100}%`;
    });
    const ja = document.documentElement.lang === 'ja';
    document.querySelector('#hit-caption').textContent = ja
      ? `上位${k}件に対象出典が入った質問数 / 対象あり22問`
      : `Queries with a target source in the top ${k} / 22 target-bearing queries`;
    document.querySelector('[data-chart-announcement]').textContent = ja
      ? `保存済みのTop ${k}集計を表示しています。`
      : `Displaying stored Top ${k} aggregates.`;
  });
}
