$(document).ready(function(){
	
	$("input.autosubmit").on("change", function(){
		var form = $(this).parents('form').first();
		$(".message", form).css("display", "block");
		$("div.paged").css("display", "none");
		form.submit();
	});
	
});