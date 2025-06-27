$(document).ready(function () {
	$('.service__form_block .panel').hide();

	$('.service__services > .panel > button.accordion').filter(function () {
		return !$(this).text().trim();
	}).remove();

	$('.salonsSlider').slick({
		arrows: true,
		slidesToShow: 4,
		infinite: true,
		prevArrow: $('.salons .leftArrow'),
		nextArrow: $('.salons .rightArrow'),
		responsive: [
			{ breakpoint: 991, settings: { centerMode: true, slidesToShow: 2 } },
			{ breakpoint: 575, settings: { slidesToShow: 1 } }
		]
	});
	$('.servicesSlider').slick({
		arrows: true,
		slidesToShow: 4,
		prevArrow: $('.services .leftArrow'),
		nextArrow: $('.services .rightArrow'),
		responsive: [
			{ breakpoint: 1199, settings: { slidesToShow: 3 } },
			{ breakpoint: 991, settings: { centerMode: true, slidesToShow: 2 } },
			{ breakpoint: 575, settings: { slidesToShow: 1 } }
		]
	});
	$('.mastersSlider').slick({
		arrows: true,
		slidesToShow: 4,
		prevArrow: $('.masters .leftArrow'),
		nextArrow: $('.masters .rightArrow'),
		responsive: [
			{ breakpoint: 1199, settings: { slidesToShow: 3 } },
			{ breakpoint: 991, settings: { slidesToShow: 2 } },
			{ breakpoint: 575, settings: { slidesToShow: 1 } }
		]
	});
	$('.reviewsSlider').slick({
		arrows: true,
		slidesToShow: 4,
		prevArrow: $('.reviews .leftArrow'),
		nextArrow: $('.reviews .rightArrow'),
		responsive: [
			{ breakpoint: 1199, settings: { slidesToShow: 3 } },
			{ breakpoint: 991, settings: { slidesToShow: 2 } },
			{ breakpoint: 575, settings: { slidesToShow: 1 } }
		]
	});

	$('.header__mobMenu').click(function () { $('#mobMenu').show(); });
	$('.mobMenuClose').click(function () { $('#mobMenu').hide(); });

	new AirDatepicker('#datepickerHere');

	$(document).on('click', '.service__form_block > button.accordion', function (e) {
		e.preventDefault();
		var $btn = $(this);
		var $panel = $btn.next('.panel');

		$panel.slideToggle(200);
		$btn.toggleClass('active');

		if ($btn.closest('.service__services').length) {
			updateCombinations();
		}
	});
	$(document).on('click', '.service__services > .panel > button.accordion', function (e) {
		e.preventDefault();
		var $btn = $(this);
		var $panel = $btn.next('.panel');
		$panel.slideToggle(200);
		$btn.toggleClass('active');
	});

	var salonBlocks = $('.service__salons   .accordion__block').toArray();
	var serviceItems = $('.service__services .accordion__block_item').toArray();
	var masterItems = $('.service__masters  .accordion__block_item').toArray();

	function bindSelection() {
		$(document).on('click', '.service__salons .accordion__block', function (e) {
			e.preventDefault();
			var $item = $(this),
				id = $item.data('id'),
				txt = $item.find('.accordion__block_intro').text() + '  ' + $item.find('.accordion__block_address').text(),
				$btn = $item.closest('.service__form_block').find('> button.accordion');

			$btn.addClass('selected').text(txt).data('id', id).removeClass('active');
			$btn.next('.panel').hide();
			updateCombinations();
		});
		$(document).on('click', '.service__services .accordion__block_item', function (e) {
			e.preventDefault();
			var $item = $(this),
				id = $item.data('id'),
				txt = $item.find('.accordion__block_item_intro').text() + '  ' + $item.find('.accordion__block_item_address').text(),
				$btn = $item.closest('.service__form_block').find('> button.accordion');

			$btn.addClass('selected').text(txt).data('id', id).removeClass('active');
			$btn.next('.panel').hide();
			updateCombinations();
		});
		$(document).on('click', '.service__masters .accordion__block_item', function (e) {
			e.preventDefault();
			var $item = $(this),
				id = $item.data('id'),
				txt = $item.find('.accordion__block_item_intro').text(),
				$btn = $item.closest('.service__form_block').find('> button.accordion');

			$btn.addClass('selected').text(txt).data('id', id).removeClass('active');
			$btn.next('.panel').hide();
			updateCombinations();
		});
	}

	function updateCombinations() {
		var salonId = $('.service__salons   > button.selected').data('id') || null;
		var serviceId = $('.service__services > button.selected').data('id') || null;
		var specialistId = $('.service__masters  > button.selected').data('id') || null;
		$.getJSON('/api/filter/', {
			salon: salonId,
			service: serviceId,
			specialist: specialistId
		}, function (data) {
			applyFilters(data, serviceId);
		});
	}

	function applyFilters(data, serviceId) {
		var allowedSalons = data.salons.map(function (o) { return o.id; });
		var allowedServices = data.services.map(function (o) { return o.id; });
		var allowedSpecialists = data.specialists.map(function (o) { return o.id; });

		salonBlocks.forEach(function (el) {
			var id = $(el).data('id');
			$(el)[allowedSalons.includes(id) ? 'show' : 'hide']();
		});

		serviceItems.forEach(function (el) {
			var id = $(el).data('id');
			$(el)[allowedServices.includes(id) ? 'show' : 'hide']();
		});

		if (!serviceId) {
			$('.service__services > .panel > button.accordion').show();
		} else {
			$('.service__services > .panel > button.accordion').each(function () {
				var hasAny = $(this).next('.panel').find('.accordion__block_item:visible').length;
				$(this)[hasAny ? 'show' : 'hide']();
			});
		}

		masterItems.forEach(function (el) {
			var id = $(el).data('id');
			$(el)[allowedSpecialists.includes(id) ? 'show' : 'hide']();
		});

		$('.service__services > .panel > button.accordion').filter(function () {
			return !$(this).text().trim();
		}).remove();
	}

	bindSelection();
	updateCombinations();

	$('.header__block_auth').click(function (e) { e.preventDefault(); $('#authModal').arcticmodal(); });
	$('.rewiewPopupOpen').click(function (e) { e.preventDefault(); $('#reviewModal').arcticmodal(); });
	$('.payPopupOpen').click(function (e) { e.preventDefault(); $('#paymentModal').arcticmodal(); });
	$('.tipsPopupOpen').click(function (e) { e.preventDefault(); $('#tipsModal').arcticmodal(); });
	$('.authPopup__form').submit(function () { $('#confirmModal').arcticmodal(); return false; });

	$(document).on('click', '.time__items .time__elems_btn', function (e) {
		e.preventDefault();
		$('.time__elems_btn').removeClass('active');
		$(this).addClass('active');
	});
	$(document).on('click', '.servicePage', function () {
		if ($('.time__elems_btn.active').length > 0 && $('.service__form_block > button.selected').length > 0) {
			$('.time__btns_next').addClass('active');
		}
	});

});
