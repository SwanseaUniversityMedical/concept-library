$(function(){
	$('body').on('click', '.js-load-modal', {modalWidth: '60%'}, formDialog.loadForm);
	$('body').on('click', '.js-load-large-modal', {modalWidth: '85%'}, formDialog.loadForm);
	
	$('#modal-section').on('submit', '.js-submit-form', formDialog.saveForm);
	
	$("[data-toggle=popover]").each(function(i, obj) {
		
		var w = $(this).attr("data-max-width");
		
		$(this).popover({
			html: true,
    		content: function() {
    		var id = $(this).attr('id')
    			return $('#popover-content-' + id).html();
    		}
    	});
    });
	
	 $(document).ajaxComplete(function() {

		$("[data-toggle=popover]").each(function(i, obj) {
			$(this).popover({
				html: true,
	    		content: function() {
	    		var id = $(this).attr('id')
	    			return $('#popover-content-' + id).html();
	    		}
	    	});
	    });
	});
});

var formDialog = (function(){
	
	var loadForm = function(e){
		e.preventDefault();
		
		var target = $(this).attr('href');		
		$(".loader").show();
		$('#modal-section .modal-content').load(target, function(){
			if(typeof e.data !== 'undefined' && e.data.modalWidth !== 'undefined'){
				$('.modal-dialog').css({width: e.data.modalWidth})
			}
			$('#modal-section').modal('show');
			$(".loader").hide();
		});
	};

	var saveForm = function(){
		var form = $(this);
		
		$.ajax({
			url:  form.attr("action"),
			data: form.serialize(),
			type: form.attr("method"),
			dataType: 'json',
			beforeSend: function(xhr, opts){
				$(".loader").show();
			},
			success: function(data){
				if(data.form_is_valid){
					$('#component-table tbody').html(data.html_component_list);
					$('#history-table tbody').html(data.html_history_list);
					$('#latest-history-ID-Div').html(data.latest_history_ID);
					$('#latest_history_id').val(data.latest_history_ID);
					$('#concept-component-form-container').html(data.add_menu_items);

					// href needs to be updated for publish concept to get latest history id
					if($('#publish2').length){
						var pub_href = $('#publish2').attr("href").split("/");
						pub_href[3] = data.latest_history_ID;
						pub_href = pub_href.join("/")
						$('#publish2').attr("href", pub_href);
					}
					
					$('#modal-section').modal('hide');
				}
				else{
					$('#modal-section .modal-content').html(data.html_form);
				}
			},
			complete: function(){
				$(".loader").hide();
			}
		});
		return false;
	};
	
	return {
		loadForm: loadForm,
		saveForm: saveForm
	}
})();
