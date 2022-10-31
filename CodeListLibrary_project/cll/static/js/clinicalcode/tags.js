var tagService = new function(){
	
	var initialize = function(){
		var elt = $('#txtTags');
		
		var tags = new Bloodhound({
			datumTokenizer: Bloodhound.tokenizers.obj.whitespace('id'),
			queryTokenizer: Bloodhound.tokenizers.whitespace,
			remote: {
				url: '/api/v1/tags-and-collections/?type=1&search=%QUERY%',
				wildcard: '%QUERY%',
			}
		});
		
		tags.initialize();
		
		$('#txtTags').tagsinput({
			itemValue: 'id',
			itemText: 'description',
			maxChars: 10,
			trimValue: true,
			allowDuplicates: false,
			freeInput: false,
			tagClass: function(item){
				if(item.get_display_display){					
					return 'label label-' + item.get_display_display;
				}
				else if(item.display)
					return 'label label-' + item.display;
				else
					return 'label label-default';
			},
			onTagExists: function(item, $tag){
				$tag.hide().fadeIn();
			},
			typeaheadjs: [{
				hint: false,
				highlight: true
			},
			{
				name: 'tagids',
				itemValue: 'id',
				displayKey: 'description',
				source: tags.ttAdapter(),
				templates: {
					empty: [
						'<ul class="list-group"><li class="list-group-item">Nothing found.</li></ul>'
					],
					suggestion: function(data){
						return '<li class="list-group-item">' + data.description + '</li>'
					}
				}
			}]
		});
	}
	
	return {
		initialize: initialize
	}
	
}