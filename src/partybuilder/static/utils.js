$(document).ready(function(){
	
	$("input.autosubmit").on("change", function(){
		var form = $(this).parents('form').first();
		$(".message", form).css("display", "block");
		if (!$(this).hasClass('retain')) {
			$(".paged").css("display", "none");
		}
		$('body').css('cursor', 'wait');
		form.submit();
	});
	
});