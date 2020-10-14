
$("#deleteBtn").click(function (event) {
	event.preventDefault();
    var form = $(this).closest("form");

  	//=============================================
	$.ajax({
		url: url_concurrency_chk,
        type: 'GET',
		data: {"latest_history_id_shown": form.find('input[name=latest_history_id_shown]').val()  
			  ,"component_id": form.find('input[name=component_id]').val()  
			},
		//dataType: 'json',
		beforeSend: function(xhr, opts){
			$(".loader").show();
		},
		success: function(data){
			//alert('check done.......');
					 
			if(data.errorMsg){
				 if(data.overrideVersion == -1){
					 alert(data.errorMsg);
					 $(".loader").hide();
				 } else {
					 confrm = false;
					 confrm = confirm(data.errorMsg);
					 if(confrm){
						 $(".loader").hide();
						 form.submit();						
						 $(this).closest("modal").modal('toggle'); //or  $('#IDModal').modal('hide');	
					 }else{
						 $(".loader").hide();
					 }
				 }
			}
				   

			if(data.successMsg){
				//alert(data.successMsg);
				$(".loader").hide();
				form.submit();						
				$(this).closest("modal").modal('toggle'); //or  $('#IDModal').modal('hide');	
			}
		},
		complete: function(){
			//$(".loader").hide();
		}
	});
    //=============================================

  });
     

    