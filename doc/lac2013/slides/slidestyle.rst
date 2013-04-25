{
  "pageSetup": {
    "width": "9in",
    "height": "6in",
    "margin-top": "0cm",
    "margin-bottom": "2mm",
    "margin-left": "0cm",
    "margin-right": "0cm",
    "margin-gutter": "0cm",
    "spacing-header": "0mm",
    "spacing-footer": "2mm",
    "firstTemplate": "slidePage"
  },
  "pageTemplates" : {
    "slidePage": {
        "showHeader": false, 
        "frames": [
            ["10%", "5%", "80%", "90%"]
        ]
    }
  },
  "styles" : [
    [ "center", {
      "parent": "bodytext", 
      "fontSize": "120%",
      "alignment": "TA_CENTER"
      }
    ],  
    ["title" , {
      "parent": "heading",
      "fontName": "stdBold",
      "fontSize": "180%",
      "alignment": "TA_CENTER",
      "keepWithNext": false,
      "spaceAfter": 1
    }],
    ["subtitle" , {
      "parent": "title",
      "fontSize": "80%",
      "spaceBefore": 0,
      "spaceAfter": 0
    }],
    ["heading1" , {
      "parent": "heading",
      "fontName": "stdBold",
      "alignment": "TA_CENTER",
      "fontSize": "140%"
    }],
    ["heading2" , {
      "parent": "heading",
      "fontName": "stdBold",
      "fontSize": "110%"
    }],
    ["heading3" , {
      "parent": "heading",
      "fontName": "stdBoldItalic",
      "fontSize": "105%"
    }
    ]
  ]
}

