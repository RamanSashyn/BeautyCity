$(document).ready(function () {
	$('.service__form_block .panel').hide();
	$('.service__services > .panel > button.accordion').filter(function () {
		return !$(this).text().trim();
	}).remove();

	function initSlider(selector, arrowContainer, extraSettings = {}) {
		const $slider = $(selector);
		const count = $slider.children().length;
		const show = count >= 4 ? 4 : count;
		$slider.slick({
			arrows: count > show,
			slidesToShow: show,
			infinite: count > show,
			prevArrow: $(`${arrowContainer} .leftArrow`),
			nextArrow: $(`${arrowContainer} .rightArrow`),
			responsive: [
				{ breakpoint: 1199, settings: { slidesToShow: 3 } },
				{ breakpoint: 991, settings: { slidesToShow: 2, centerMode: true } },
				{ breakpoint: 575, settings: { slidesToShow: 1 } }
			],
			...extraSettings
		});
	}

	initSlider('.salonsSlider', '.salons', {
		responsive: [
			{ breakpoint: 991, settings: { centerMode: true, slidesToShow: 2 } },
			{ breakpoint: 575, settings: { slidesToShow: 1 } }
		]
	});
	initSlider('.servicesSlider', '.services');
	initSlider('.mastersSlider', '.masters');
	initSlider('.reviewsSlider', '.reviews');

	$('.header__mobMenu').click(() => $('#mobMenu').show());
	$('.mobMenuClose').click(() => $('#mobMenu').hide());

	function loadSlots(selectedDate) {
		const salonId = $('.service__salons > button.selected').data('id') || '';
		const specialistId = $('.service__masters > button.selected').data('id') || '';
		const serviceId = $('.service__services > button.selected').data('id') || '';
		const date = selectedDate || $('#datepickerHere').val() || new Date().toISOString().split('T')[0];
		const params = new URLSearchParams({ date });
		if (salonId) params.append('salon_id', salonId);
		if (specialistId) params.append('specialist_id', specialistId);
		if (serviceId) params.append('service_id', serviceId);
		$.getJSON(`/api/slots-by-specialist/?${params}`, function (slots) {
			const sections = {
				morning: $('.time__items').eq(0).find('.time__elems_elem').empty(),
				day: $('.time__items').eq(1).find('.time__elems_elem').empty(),
				evening: $('.time__items').eq(2).find('.time__elems_elem').empty(),
			};
			slots.forEach(slot => {
				const btn = $('<button>').addClass('time__elems_btn').attr({ type: 'button', 'data-slot-id': slot.id }).text(slot.time);
				(slot.hour < 12 ? sections.morning : slot.hour < 18 ? sections.day : sections.evening).append(btn);
			});
		});
	}

	new AirDatepicker('#datepickerHere', {
		dateFormat: 'yyyy-MM-dd',
		onSelect({ formattedDate }) {
			loadSlots(formattedDate);
			updateCombinations();
		}
	});

	$(document).on('click', '.service__form_block > button.accordion, .service__services > .panel > button.accordion', function (e) {
		e.preventDefault();
		$(this).next('.panel').slideToggle(200);
		$(this).toggleClass('active');
		if ($(this).closest('.service__services').length) updateCombinations();
	});

	function handleSelection(blockSelector, getText) {
		$(document).on('click', blockSelector, function (e) {
			e.preventDefault();
			const $it = $(this), id = $it.data('id');
			const txt = getText($it);
			const $btn = $it.closest('.service__form_block').find('> button.accordion');
			$btn.addClass('selected').text(txt).data('id', id).removeClass('active');
			$btn.next('.panel').hide();
			loadSlots();
			updateCombinations();
		});
	}

	handleSelection('.service__salons .accordion__block', $it => `${$it.find('.accordion__block_intro').text()}  ${$it.find('.accordion__block_address').text()}`);
	handleSelection('.service__services .accordion__block_item', $it => `${$it.find('.accordion__block_item_intro').text()}  ${$it.find('.accordion__block_item_address').text()}`);
	handleSelection('.service__masters .accordion__block_item', $it => $it.find('.accordion__block_item_intro').text());

	$(document).on('click', '.time__items .time__elems_btn', function (e) {
		e.preventDefault();
		$('.time__elems_btn').removeClass('active');
		$(this).addClass('active');
		updateCombinations();
	});

	function updateCombinations() {
		const getId = sel => $(`.service__${sel} > button.selected`).data('id') || null;
		const time = $('.time__elems_btn.active').text() || null;
		const date = $('#datepickerHere').val() || new Date().toISOString().split('T')[0];
		const params = new URLSearchParams({ date });
		['salon', 'service', 'specialist'].forEach(key => {
			const id = getId(key);
			if (id) params.append(key, id);
		});
		if (time) params.append('time', time);
		$.getJSON(`/api/filter/?${params}`, data => applyFilters(data, getId('service')));
	}

	function toggleVisibility($items, allowedIds) {
		$items.each((_, el) => {
			const $el = $(el);
			$el.toggle(allowedIds.includes($el.data('id')));
		});
	}

	function applyFilters(data, serviceId) {
		toggleVisibility($('.service__salons .accordion__block'), data.salons.map(o => o.id));
		toggleVisibility($('.service__services .accordion__block_item'), data.services.map(o => o.id));
		toggleVisibility($('.service__masters .accordion__block_item'), data.specialists.map(o => o.id));

		const $accordionBtns = $('.service__services > .panel > button.accordion');
		if (!serviceId) {
			$accordionBtns.show();
		} else {
			$accordionBtns.each(function () {
				const hasAny = $(this).next('.panel').find('.accordion__block_item:visible').length;
				$(this).toggle(hasAny);
			});
		}
		$accordionBtns.filter(function () { return !$(this).text().trim(); }).remove();
	}

	loadSlots();
	updateCombinations();

	const isLoggedIn = document.body.dataset.isLoggedIn === 'true';
	$('.header__block_auth').click(function (e) {
		if (!isLoggedIn) {
			e.preventDefault();
			$('#authModal').arcticmodal();
		}
	});

	[
		{ sel: '.rewiewPopupOpen', modal: '#reviewModal' },
		{ sel: '.payPopupOpen', modal: '#paymentModal' },
		{ sel: '.tipsPopupOpen', modal: '#tipsModal' }
	].forEach(({ sel, modal }) => $(sel).click(e => { e.preventDefault(); $(modal).arcticmodal(); }));

	$('.authPopup__form').submit(() => { $('#confirmModal').arcticmodal(); return true; });

	$(document).on('click', '.servicePage', function () {
		if ($('.time__elems_btn.active').length && $('.service__form_block > button.selected').length) {
			$('.time__btns_next').addClass('active');
		}
	});

	$(document).on('click', '.time__btns_next.active', function (e) {
		e.preventDefault();
		const getId = sel => $(`.service__${sel} > button.selected`).data('id');
		const slotId = $('.time__elems_btn.active').data('slot-id');
		const salonId = getId('salons'), serviceId = getId('services'), specialistId = getId('masters');
		if (!slotId || !salonId || !serviceId || !specialistId) return alert('Пожалуйста, выберите все поля.');
		$.post('/api/book/', {
			slot_id: slotId,
			salon_id: salonId,
			service_id: serviceId,
			specialist_id: specialistId,
			csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
		}).done(res => {
			if (res.success && res.redirect_url) window.location.href = res.redirect_url;
			else alert('Ошибка при записи. Попробуйте снова.');
		});
	});

	ymaps.ready(function () {
		if (!document.getElementById('map')) return;
		const points = window.mapPoints || [];
		const center = points.length ? [points[0].lat, points[0].lon] : [59.94, 30.32];
		const myMap = new ymaps.Map('map', {
			center,
			zoom: 12,
			controls: ['zoomControl', 'fullscreenControl']
		});
		points.forEach(pt => myMap.geoObjects.add(
			new ymaps.Placemark([pt.lat, pt.lon], { hintContent: pt.hint }, { preset: 'islands#redDotIcon' })
		));
	});
});
