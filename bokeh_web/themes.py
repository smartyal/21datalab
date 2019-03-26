





palette = {
    #Palette http://paletton.com/#uid=71o0D0kw0relCyPrAvBA3m9HPgW, starting with base color d9b100, then dist 40° , four colors
    "color-primary-0": "#D9B100",	# Main Primary color */
    "color-primary-1": "#FFE053",
    "color-primary-2": "#FCD423",
    "color-primary-3": "#B09000",
    "color-primary-4": "#876E00",

    "color-secondary-1-0": "#74048F",	# Main Secondary color (1) */
    "color-secondary-1-1": "#993DB0",
    "color-secondary-1-2": "#8B1BA6",
    "color-secondary-1-3": "#5E0374",
    "color-secondary-1-4": "#480259",

    "color-secondary-2-0": "#C0D500",	# Main Secondary color (2) */
    "color-secondary-2-1": "#EAFB51",
    "color-secondary-2-2": "#E3F722",
    "color-secondary-2-3": "#9CAD00",
    "color-secondary-2-4": "#788400",

    "color-complement-0": "#2D1296",	# Main Complement color */
    "color-complement-1": "#614AB7",
    "color-complement-2": "#452AAE",
    "color-complement-3": "#230C7A",
    "color-complement-4": "#19075D",

    #from https://www.w3schools.com/colors/colors_picker.asp
    'bw00%':'#000000',
    'bw10%': '#1a1a1a',
    'bw20%': '#333333',
    'bw30%': '#4d4d4d',
    'bw40%': '#666666',
    'bw50%': '#808080',
    'bw60%': '#999999',
    'bw70%': '#b3b3b3',
    'bw80%': '#cccccc',
    'bw90%': '#e6e6e6',
    'bw100%': '#ffffff',  #full white

    '21yellow': '#d9b100',  ## equals 43% RGB = 217,177,0
    '21yellow20%': '#665300',
    '21yellow30%': '#332a00',
    '21yellow40%': '#cca700',
    '21yellow50%': '#ffd000',
    '21yellow60%': '#ffda33',
    '21yellow70%': '#ffe366',
    '21yellow80%': '#ffec99',
    '21yellow90%': '#fff6cc',

    'alarm' : '#d92200'
}

whiteLineColors =[
'#d9b100',
'#002699',
'#660000',
"#8080ff",
"#66ff66",
palette['alarm']
]

defaultLineColors=[
palette['21yellow'],
palette["21yellow20%"],
palette['bw70%'],
palette["21yellow70%"],
palette["bw20%"],
palette['alarm']
]


defaultTheme = {
    'attrs' : {
        'Figure' : {
                'background_fill_color': palette['bw10%'],
                'border_fill_color': palette['bw10%'],
                'outline_line_color': palette['bw80%'],
            },
        'Grid': {
            'grid_line_color':palette['bw30%']
        },
        'Title': {
            'text_color': palette['bw80%']
        },
        'Legend':{
            'background_fill_color': palette['bw10%'],
            'label_text_color': palette['bw80%']
        }
    }
}

whiteTheme ={
'attrs' : {
        'Figure' : {
                'background_fill_color': "white",
                'border_fill_color': "white",
                'outline_line_color':"black",
            },
        'Grid': {
            'grid_line_color':palette['bw60%']
        },
        'Title': {
            'text_color': palette['bw30%']
        },
        'Legend':{
            'background_fill_color': palette['bw80%'],
            'label_text_color': palette['bw20%']
        }
    }

}



textcolor=palette["bw80%"]
lineColors = whiteLineColors

