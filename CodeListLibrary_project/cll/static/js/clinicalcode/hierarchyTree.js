var tree = $("#tree").text();

comps = JSON.parse(tree);

var counter = 1;

/* creates tree of components */
function traverse(compJson, listId, lvl) {
    var myList = $("#" + listId);  
    if (compJson !== null && typeof compJson == "object") {            
        Object.entries(compJson).forEach(([key, value]) => {

            var newListId = null;
            var padding = (lvl === 1) ? 15 : 15 + (lvl * 7.5);
            var badge = value["logical_type"] === "Add Codes" ? "success" : "danger";
            if (value.hasOwnProperty("is_concept")) {
                if(value["is_concept"] === true) {
                    newListId = counter; 
                    newList = "<a href=#" + newListId + " class='list-group-item arrow' data-toggle='collapse' style='padding-left: " + padding + "px;'>"
                               + "<i class='glyphicon glyphicon-chevron-right'>"
                                    + "<b>" + value["name"] + "</b>" 
                               + "</i>"
                               + "<span class='badges'>"
                                    + "<span class='badge badge progress-bar-secondary'>Version:<span style='padding-left:5px;'>" + value["version"] + "</span></span>"
                                    + "<span class='badge badge progress-bar-secondary'>Type:<span style='padding-left:5px;'>" + value["type"] + "</span></span>"
                                    + "<span class='badge badge progress-bar-" + badge +"'>" + value["logical_type"] + "</span>"
                               + "</span>"
                            + "</a><div class='list-group collapse' id=" + newListId  + "></div>";
                    myList.append(newList);
                } else {
                    padding += 15;
                    id = counter;
                    newEelment = "<a class='list-group-item' style='padding-left: " 
                                + padding + "px;'>" + value["name"]
                                + "<span class='badges'>" 
                                    + "<span class='badge badge progress-bar-secondary'>Type:<span style='padding-left:5px;'>" + value["type"] + "</span></span>"
                                    + "<span class='badge badge progress-bar-" + badge + "'>" + value["logical_type"] + "</span>"
                                    + "<span style='margin-left:10px;' type='button' class='' data-toggle='modal' data-target='#" 
                                    + id +"'>"
                                    + "<button tabindex='0' id='hover-" + id +  "' style='margin-left:10px;' type='button' class='pop btn btn-info btn-xs' data-trigger='hover'" 
                                    + "data-toggle='popover' data-container='body' data-placement='left'><i class='glyphicon glyphicon-search'></i></button>" 
                                    + "</span>"
                                    
                                + "</span>"
                                + "</a>";
                                
                    myList.append(newEelment);

                    /* create modals for codes */
                    codes = JSON.parse(value["codes"]);
                    createModalsForCodes(codes, id);
                }
                counter++;
            }
            if (newListId === null) {
                traverse(value, listId, lvl + 1);
            } else {
                traverse(value, newListId, lvl + 1);
            }
        });
    }
}

traverse(comps, "root", 1);

/* TO DO new function for codes*/
function createModalsForCodes(codes, history_id) {
    var modal = '<div class="modal fade in" id="' + history_id + '">'
                    +'<div class="modal-dialog" style="width: 60%;">'
                        +'<div class="modal-content">'
                            +'<div class="modal-header">' 
                            + '<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                            +     '<span aria-hidden="true">&times;</span>'
                            +'</button>'
                            + '<h4 class="modal-title"><i class="fa fa-barcode" aria-hidden="true"></i> Codes</h4>'
                            +'</div>'
                            +'<div class="modal-body">'
                                +'<div class="form-horizontal">'
                                    +'<div class="row">'
                                        +'<div class="col-md-12">'
                                            +'<div id="table' + history_id +'" class="clusterize" class="pre-scrollable">'
                                                +'<table class="table table-striped small-table table-hover" style="margin-bottom: 0px;">'
                                                    +'<thead>'
                                                        +'<tr>'
                                                            + '<th style="width: 120px; border: none;">Code</th>'
                                                            +'<th style="border: none;">Description</th>'
                                                        +'</tr>'
                                                    +'</thead>'
                                                    +'<tbody id="codes' + history_id + '" class="clusterize-content" />'
                                                +'</table>'
                                            +'</div>'
                                        +'</div>'
                                    +'</div>'
                                +'</div>'
                                +'<div class="row">'
                                    +'<div class="col-md-12 text-right">'
                                        +'<span class="expressionAmount label label-primary"></span>'
                                    +'</div>'
                                +'</div>'
                            +'</div>'
                            +'<div class="modal-footer">'
                                +'<button type="button" class="btn btn-default" data-dismiss="modal">Close</button>'
                            +'</div>'
                        +'</div>'
                    +'</div>'
                +'</div>'
            
            $('#modals').append(modal);
    
    var tableBody = $('#codes' + history_id);
    /* Go through codes and add them to a table*/
    if (codes !== null && typeof codes == "object") {            
        Object.entries(codes).forEach(([key, value]) => {
            row = '<tr>'
                    +'<td>' + value['code'] + '</td>'
                    +'<td>' + value['description'] +'</td>'
                 +'</tr>'
            tableBody.append(row);
        });
    }

}

/* activate popovers*/
$('.pop').each(function(i, obj) {
    var id = $(this).attr('id');
    id = id.split('-');
    $(obj).popover({
        html: true,
        content: function() {
            return $('#table' + id[1]).html();
        }
    });
});

/* change arrow icons when clicked */
$(function() {
    $('.arrow').on('click', function() {
      $('.glyphicon', this)
        .toggleClass('glyphicon-chevron-right')
        .toggleClass('glyphicon-chevron-down');
    });   
});