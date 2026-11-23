/*
 * Vidvys egen videospelare.
 *
 * Gör om varje <div class="showreel"><video controls ...></video></div> till en
 * spelare med stor startknapp, tidslinje, tid, ljud och helskärm, utan
 * nedladdning, uppspelningshastighet eller bild-i-bild. Utan JavaScript
 * används webbläsarens vanliga spelare (med nedladdning avstängd där det går).
 */
(function () {
    'use strict';

    const IKON = {
        play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11-6.86a1 1 0 0 0 0-1.72l-11-6.86A1 1 0 0 0 8 5.14z"/></svg>',
        paus: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>',
        ljud: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        tyst: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 9.5l5 5m0-5l-5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        hel: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        ut: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    };

    function tid(s) {
        if (!isFinite(s)) s = 0;
        const m = Math.floor(s / 60);
        const sek = Math.floor(s % 60);
        return m + ':' + (sek < 10 ? '0' : '') + sek;
    }

    function knapp(klass, etikett, ikon) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'vp-knapp ' + klass;
        b.setAttribute('aria-label', etikett);
        b.innerHTML = ikon;
        return b;
    }

    function bygg(ram) {
        const video = ram.querySelector('video');
        if (!video || ram.classList.contains('vp')) return;

        video.removeAttribute('controls');
        video.setAttribute('controlslist', 'nodownload noplaybackrate noremoteplayback');
        video.disablePictureInPicture = true;
        video.setAttribute('disablepictureinpicture', '');
        video.setAttribute('disableremoteplayback', '');
        video.setAttribute('tabindex', '-1');
        ram.classList.add('vp', 'vp-start');
        ram.setAttribute('tabindex', '0');
        ram.setAttribute('role', 'region');
        ram.setAttribute('aria-label', video.getAttribute('aria-label') || 'Film');

        const stor = knapp('vp-stor', 'Spela filmen', IKON.play);

        const rad = document.createElement('div');
        rad.className = 'vp-rad';
        const spela = knapp('vp-spela', 'Spela', IKON.play);
        const nu = document.createElement('span');
        nu.className = 'vp-tid';
        nu.textContent = '0:00';
        const linje = document.createElement('div');
        linje.className = 'vp-linje';
        linje.setAttribute('role', 'slider');
        linje.setAttribute('aria-label', 'Spola');
        linje.setAttribute('aria-valuemin', '0');
        linje.setAttribute('tabindex', '0');
        linje.innerHTML = '<div class="vp-laddat"></div><div class="vp-spelat"></div><div class="vp-prick"></div>';
        const total = document.createElement('span');
        total.className = 'vp-tid';
        total.textContent = '0:00';
        const ljud = knapp('vp-ljud', 'Stäng av ljudet', IKON.ljud);
        const hel = knapp('vp-hel', 'Helskärm', IKON.hel);
        rad.append(spela, nu, linje, total, ljud, hel);
        ram.append(stor, rad);

        const spelat = linje.querySelector('.vp-spelat');
        const prick = linje.querySelector('.vp-prick');
        const laddat = linje.querySelector('.vp-laddat');

        function vaxla() {
            if (video.paused || video.ended) video.play(); else video.pause();
        }

        let gomTimer;
        function visa() {
            ram.classList.add('vp-visa');
            clearTimeout(gomTimer);
            if (!video.paused) gomTimer = setTimeout(() => ram.classList.remove('vp-visa'), 2500);
        }

        function uppdatera() {
            const d = video.duration || 0;
            const p = d ? video.currentTime / d * 100 : 0;
            spelat.style.width = p + '%';
            prick.style.left = p + '%';
            nu.textContent = tid(video.currentTime);
            linje.setAttribute('aria-valuemax', String(Math.round(d)));
            linje.setAttribute('aria-valuenow', String(Math.round(video.currentTime)));
            linje.setAttribute('aria-valuetext', tid(video.currentTime) + ' av ' + tid(d));
        }

        stor.addEventListener('click', vaxla);
        spela.addEventListener('click', vaxla);
        video.addEventListener('click', () => { vaxla(); visa(); });

        video.addEventListener('play', () => {
            ram.classList.remove('vp-start');
            ram.classList.add('vp-spelar');
            spela.innerHTML = IKON.paus;
            spela.setAttribute('aria-label', 'Pausa');
            visa();
        });
        video.addEventListener('pause', () => {
            ram.classList.remove('vp-spelar');
            spela.innerHTML = IKON.play;
            spela.setAttribute('aria-label', 'Spela');
            visa();
        });
        video.addEventListener('ended', () => {
            ram.classList.add('vp-start');
            video.currentTime = 0;
        });
        video.addEventListener('loadedmetadata', () => { total.textContent = tid(video.duration); uppdatera(); });
        video.addEventListener('timeupdate', uppdatera);
        video.addEventListener('progress', () => {
            const d = video.duration;
            if (d && video.buffered.length) {
                laddat.style.width = video.buffered.end(video.buffered.length - 1) / d * 100 + '%';
            }
        });
        video.addEventListener('waiting', () => ram.classList.add('vp-vantar'));
        video.addEventListener('playing', () => ram.classList.remove('vp-vantar'));

        // Spola genom att klicka eller dra på tidslinjen
        function spolaTill(e) {
            const r = linje.getBoundingClientRect();
            const x = Math.min(Math.max(e.clientX - r.left, 0), r.width);
            if (video.duration) video.currentTime = x / r.width * video.duration;
            uppdatera();
        }
        linje.addEventListener('pointerdown', e => {
            linje.setPointerCapture(e.pointerId);
            ram.classList.add('vp-drar');
            spolaTill(e);
            const flytta = ev => spolaTill(ev);
            const slapp = () => {
                ram.classList.remove('vp-drar');
                linje.removeEventListener('pointermove', flytta);
                linje.removeEventListener('pointerup', slapp);
                linje.removeEventListener('pointercancel', slapp);
            };
            linje.addEventListener('pointermove', flytta);
            linje.addEventListener('pointerup', slapp);
            linje.addEventListener('pointercancel', slapp);
        });
        linje.addEventListener('keydown', e => {
            if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                e.preventDefault();
                e.stopPropagation();
                video.currentTime += e.key === 'ArrowRight' ? 5 : -5;
            }
        });

        ljud.addEventListener('click', () => {
            video.muted = !video.muted;
        });
        video.addEventListener('volumechange', () => {
            ljud.innerHTML = video.muted ? IKON.tyst : IKON.ljud;
            ljud.setAttribute('aria-label', video.muted ? 'Slå på ljudet' : 'Stäng av ljudet');
        });

        // Helskärm på hela spelaren så att de egna kontrollerna följer med.
        // iPhone kan bara visa själva filmen i helskärm och använder då sin egen spelare.
        hel.addEventListener('click', () => {
            if (document.fullscreenElement || document.webkitFullscreenElement) {
                (document.exitFullscreen || document.webkitExitFullscreen).call(document);
            } else if (ram.requestFullscreen) {
                ram.requestFullscreen();
            } else if (ram.webkitRequestFullscreen) {
                ram.webkitRequestFullscreen();
            } else if (video.webkitEnterFullscreen) {
                video.webkitEnterFullscreen();
            }
        });
        function helskarmAndrad() {
            const i = (document.fullscreenElement || document.webkitFullscreenElement) === ram;
            ram.classList.toggle('vp-helskarm', i);
            hel.innerHTML = i ? IKON.ut : IKON.hel;
            hel.setAttribute('aria-label', i ? 'Lämna helskärm' : 'Helskärm');
        }
        document.addEventListener('fullscreenchange', helskarmAndrad);
        document.addEventListener('webkitfullscreenchange', helskarmAndrad);

        ram.addEventListener('pointermove', visa);
        ram.addEventListener('pointerleave', () => { if (!video.paused) ram.classList.remove('vp-visa'); });
        ram.addEventListener('focusin', visa);
        ram.addEventListener('contextmenu', e => e.preventDefault());
        ram.addEventListener('keydown', e => {
            if (e.target.closest('.vp-knapp')) return;
            if (e.key === ' ' || e.key === 'k') { e.preventDefault(); vaxla(); }
            else if (e.key === 'f') hel.click();
            else if (e.key === 'm') ljud.click();
            else if (e.key === 'ArrowRight') video.currentTime += 5;
            else if (e.key === 'ArrowLeft') video.currentTime -= 5;
            else return;
            visa();
        });
    }

    document.querySelectorAll('.showreel').forEach(bygg);
})();
