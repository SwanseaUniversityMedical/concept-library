var dataService = new function(){
	
	var serviceBase = '/components/',
			  
	getCodesByRegex = function(concept, searchText, regexCode, logicalType, regexType, csrfmiddlewaretoken, searchColumn, case_sensitive_search, callback){		
		$.ajax({
			type: 'POST',
			url: serviceBase + concept + '/searchcodes/',
			data: {search_text: searchText, search_params: '', regex_code: regexCode, logical_type: logicalType
				, regex_type: regexType, csrfmiddlewaretoken:csrfmiddlewaretoken, column_search: searchColumn
				, case_sensitive_search: case_sensitive_search
				},
			success: function(data){
				callback(data);
			}
		});
	};

	getCodes = function(concept, pk, callback){		
		$.getJSON(serviceBase + concept + '/expression/' + pk + '/getcodes/', function(data){
			callback(data);
		});
	};
	
	getCodesByCodeList = function(code_list_id, callback){		
		$.getJSON('/api/codes/?code_list_id=' + code_list_id, function(data){
			callback(data);
		});
	};
	
	getComponents = function(concept, callback){
			
		$.getJSON('/concepts/' + concept + '/components/', function(data){
			callback(data);
		});
	};

	
	getConceptUniqueCodes = function(concept, callback){		
		$.getJSON('/concepts/' + concept + '/uniquecodes/', function(data){
			callback(data);
		});
	};
	
	getConceptUniqueCodesByVersion = function(concept, version, callback){		
		$.getJSON('/concepts/' + concept + '/uniquecodesbyversion/'+ version +'/', function(data){
			callback(data);
		});
	};
	
	getPhenotypeUniqueCodesByVersion = function(phenotype, version, callback){		
		$.getJSON('/phenotype/' + phenotype + '/uniquecodesbyversion/'+ version +'/', function(data){
			callback(data);
		});
	};
	
	getConceptVersions = function(concept, version, indx, callback){		
		$.getJSON('/concepts/' + concept + '/conceptversions/'+ version +'/'+ indx +'/', function(data){
			callback(data);
		});
	};	
	
	searchCodeList = function(concept, searchText, searchParams, sqlRules, logicalType, csrfmiddlewaretoken, latest_history_id_shown, callback){
		$.ajax({
			type: 'POST',
			url: serviceBase + concept + '/querybuilder/search/',
			data: {search_text: searchText
				, search_params: JSON.stringify(searchParams)
				, logical_type: logicalType
				, csrfmiddlewaretoken:csrfmiddlewaretoken
				, latest_history_id_shown: latest_history_id_shown
			},
			success: function(data){
				callback(data);
			}
		});
	};
	
	searchConcepts = function(search, callback){
		$.getJSON('/api/concepts/?search=' + search, function(data){
			callback(data);
		});
	};
	
	return {
		getCodesByCodeList: getCodesByCodeList,
		getCodesByRegex: getCodesByRegex,
		getCodes: getCodes,
		getComponents: getComponents,
		searchCodeList: searchCodeList,
		searchConcepts: searchConcepts,
		getConceptUniqueCodes: getConceptUniqueCodes,
		getConceptVersions: getConceptVersions,
		getConceptUniqueCodesByVersion: getConceptUniqueCodesByVersion,
		getPhenotypeUniqueCodesByVersion: getPhenotypeUniqueCodesByVersion
	}
}