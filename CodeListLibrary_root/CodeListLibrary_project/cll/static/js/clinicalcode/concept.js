$(function(){
	$('#modal-section').on('submit', '.js-fork-submit-form', conceptFormDialog.saveForkForm);
});

var conceptFormDialog = (function(){
	
	var saveForkForm = function(){
		var form = $(this);
		
		$.ajax({
			url: form.attr("action"),
			data: form.serialize(),
			type: form.attr("method"),
			dataType: 'json',
			beforeSend: function(xhr, opts){
				$(".loader").show();
			},
			success: function(data){
				// Hide any Django originated messages which, by this point,
				// refer to the previous action.
				$('.alert').hide();
				// Place the Fork message within the concept/form.
				if(data.form_is_valid){
					$('#error-message').hide();
					$('#success-message').show();
					$('#success-message').html(data.message);
					
					$('#modal-section').modal('hide');
				}else{
					$('#success-message').hide();
					$('#error-message').show();
					$('#error-message').html(data.message);
					
					$('#modal-section').modal('hide');
				}
			},
			complete: function(){
				$(".loader").hide();
			}
		});
		return false;
	};

	return {
		saveForkForm: saveForkForm,
	}
})();