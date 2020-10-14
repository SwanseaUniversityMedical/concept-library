var clusterArea = (function(){
	var rows = [];
	
	var clusterize = null;
	
	var initClusterize = function(scrollId, contentId){
		var opts = {
			scrollId: 'scrollArea',
			contentId: 'contentArea'
		}
		clusterArea.clusterize = new Clusterize(opts);
	};
	
	return {
		rows: rows,
		clusterize: clusterize,
		initClusterize: initClusterize,
	}
})();

var clusterAreaCodes = (function(){
	var rows = [];
	
	var clusterize = null;
	
	var initClusterize = function(scrollId, contentId){
		var opts = {
			scrollId: 'scrollAreaCodes',
			contentId: 'contentAreaCodes'
		}
		clusterAreaCodes.clusterize = new Clusterize(opts);
	};
	
	return {
		rows: rows,
		clusterize: clusterize,
		initClusterize: initClusterize,
	}
})();