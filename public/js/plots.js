
var indexMap = {"thumbnails":{"width": 0, "height": 0}, "search":""};
var page_loads = 0;
var next_runNum, prev_runNum;
response = {};
run_list = [];

// Fetch object pased from index
function fetch_object() {
    var url = document.location.href.split("#")[0],
        params = url.split('?')[1].split('&'), 
        tmp;
    for (var i = 0, l = params.length; i < l; i++) {
        tmp = params[i].split('=');
        response[tmp[0]] = tmp[1];
    }
    response["query"] = unescape(response["query"]).split(",");
    console.log(response);
}
// Pass query to main submit page
function submit(query) {
    localStorage["external_query"] = JSON.stringify(query);
    document.location.href="./";
}

$(function() {
    page_loads++;
    console.log(localStorage);
    load_page(php_out);
});

function load_page(php_out) {
    var data = make_json(php_out);
    filter(data);
    fill_sections(data);
    if (page_loads == 1) {
        try {
            // Fetch query info from URL
            fetch_object();
            localStorage["data"] = response["query"][0];
            localStorage["ref"] = response["query"][1];
            localStorage["user_id"] = response["query"][2];
            localStorage["series"] = response["query"][3];
            localStorage["sample"] = response["query"][4];
            localStorage["subsystem"] = response["query"][5];
            console.log(localStorage);
            // Fill information table
            $("#data_text").text(response["query"][0]);
            $("#ref_text").text(response["query"][1]);
            $("#series_text").text(response["query"][3]);
            $("#sample_text").text(response["query"][4]);
            $("#subsys_text").text(response["query"][5]);
            $("#info_table").show();
            // Hide table if no query in localStorage
            if (response["query"][0] == "" || response["query"][1] == "") {
                $("#info_table").hide();
            }
        }
        catch(TypeError) {
            if (localStorage.hasOwnProperty("data")) {
                $("#data_title").text(localStorage["data"]);
                $("#ref_title").text(localStorage["ref"]);
                $("#title_wells").show();
            }
            else {
                $("#title_wells").hide();
            } } }
    $('[id^=img_]').mouseenter(
        function() {
            // Dynamic Well Preview
            $("#preview").attr("src", $(this).attr("src"));

            // Dynamic Well Tooltip
            new_txt = data[Number($(this).attr('id').split("_")[1])]["txt_path"];
            if (new_txt != "None"){
                $("#tooltip").show();
                $("#tooltip").load(new_txt);
            }
            else {
                $("#tooltip").hide();
            }
        } 
    );

    // Buttons for submitting same query with next or previous run
    // Grab next and previous runs for button functionality
    var rReq;
    rReq = $.getJSON("cgi-bin/handler.py",
        {type: "getRuns", series: localStorage["series"], sample: localStorage["sample"]},
        function(res) {
            $("#next_run").attr('disabled', 'disabled');
            $("#prev_run").attr('disabled', 'disabled');
            console.log("response:");
            var runLink_list = (res["response"]["runs"]);
            // Grab run numbers from list of html links ripped from online GUI
            var run_num;
            for (var i = 0; i < runLink_list.length; i++) {
                run_num = Number(runLink_list[i]["name"]);
                run_list.push(run_num);
            }
            run_list.sort();
            next_runNum = run_list[run_list.indexOf(Number(localStorage["data"])) + 1];
            prev_runNum = run_list[run_list.indexOf(Number(localStorage["data"])) - 1];
            $("#next_run").removeAttr('disabled');
            $("#prev_run").removeAttr('disabled');
        });
    // Get next and previous runs
    $("#next_run").click(function(){
        var query = {
            "type": "retrieve_data",
            "series": localStorage["series"],
            "sample": localStorage["sample"],
            "subsystem": localStorage["subsystem"],
            "data_info": next_runNum.toString(),
            "ref_info": localStorage["ref"],
            "user_id": Date.now(),
        };
        submit(query);
    });
    $("#prev_run").click(function(){
        var query = {
            "type": "retrieve_data",
            "series": localStorage["series"],
            "sample": localStorage["sample"],
            "subsystem": localStorage["subsystem"],
            "data_info": prev_runNum.toString(),
            "ref_info": localStorage["ref"],
            "user_id": Date.now(),
        };
        submit(query);
    });
}

function make_json(php_out) {
    var new_json = [];
    
    for (var i = 0; i < php_out.length; i++) {
        var img_obj = php_out[i];
        var png_path = img_obj["png_path"];
        var pdf_path = img_obj["pdf_path"];
        var txt_path = img_obj["txt_path"];
        var width = img_obj["width"];
        var height = img_obj["height"];
        var name = png_path.split('/').reverse()[0].split('.')[0];

        // Get divisor for image dimensions
        var div = get_div(Math.max(width, height));
        indexMap["thumbnails"]["width"] = width/div;
        indexMap["thumbnails"]["height"] = height/div;

        new_json.push({
            "name": name,
            "png_path": png_path,
            "pdf_path": pdf_path,
            "txt_path": txt_path,
            "width": indexMap["thumbnails"]["width"],
            "height": indexMap["thumbnails"]["height"],
            "hidden": false,
        });

    }                
    
    return new_json;
}

function get_div(max_length) {
    var divisor = 1;
    while (true) {
        if (max_length/divisor <= 250) {
            return divisor;
        }
        divisor+=0.5;
    }
}

function refresh() {
    page_loads++;
    load_page(php_out);
}

function filter(data) {

    var input = document.getElementById('search');
    if (page_loads == 1 && window.location.hash != "") {
        var search = window.location.hash.split("#")[1];
    }
    else{
        if (input == "") {
            window.location.hash = "";
        }
        var search = input.value;
        window.location.hash = search;
    }
    indexMap["search"] = search;
    for (var i = 0; i < data.length; i++) {
        if (data[i]["name"].indexOf(search) < 0) {
            data[i]["hidden"] = true;
        }
    }

    return data;
}

function set_grid(data) {
    var container = $("#section_1");
    var counter = 0;

    container.html("");

    for (var i = 0; i < (data.length + data.length % 3); i+=3) {
        var toappend = "";

        //Draw thumbnails
        toappend += "<div class='row'>";
        toappend += "   <div class='text-center'>"
        for (var j = 0; j < 3; j++){
            toappend +=     ("<div id=grid_" + (i + j) + " class='col-lg-4'></div>");
            counter++;
        }
        toappend += "   </div>"
        toappend += "</div>";
        container.append(toappend);
    }
}

function fill_grid(data) {

    var counter = 0;
    var new_search = "";

    var true_count = 0;
    for (var i = 0; i < data.length; i++) {
        if (data[i]["hidden"]) {
            true_count++;
            continue;
        }

        var new_split = "";
        var html_name = "";

        if (indexMap["search"] != "") {
            new_search = indexMap["search"];
            new_split = data[i]["name"].split(new_search);
            new_name = "";

            for (var j = 0; j < new_split.length; j++) {
                new_name += new_split[j];
                html_name += new_split[j];
                if (data[i]["name"].indexOf(new_name + new_search) != -1) {
                    new_name += new_search;
                    html_name += "<font class='bg-success'>"+new_search+"</font>";
                }
            }
        }

        else {
            html_name = data[i]["name"];
        }

        $("#grid_" + counter).append("<a href="+data[i]["pdf_path"]+"><h4>"+html_name+"</h4></a><a href="+data[i]["pdf_path"]+"><img id=img_"+true_count+" src="+data[i]["png_path"]+" width="+data[i]["width"]+" height="+data[i]["height"]+"></a>");
        true_count++;
        counter++;
    }
}

function fill_sections(data) {
    set_grid(data);
    fill_grid(data);
}
