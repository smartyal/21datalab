# Super Context Menu
Customizable context menu based on jQuery

## Getting started
To use Super Context Menu, simply clone or download and include the script and the style in your HTML. 
Super Context Menu requires jQuery to operate properly!

```
<link rel="stylesheet" href="<your folder>/context-menu.min.css">
<script type="application/javascript" src="<your folder>/context-menu.min.js">
```

## Basics
Once included, Super Context Menu provides a superCm object that can be used to customizable context menus.

### Creating a menu
To display the context menu on right click, you can use the `contextmenu` event handler. Inside the handler, invoke `superCm.createMenu` while passing the event object to create the menu as you like. 

The first argument `options` is an array of object that contains the options to be put in the menu, the second argument `event` is the event object from the event handler parameter.

Be sure to invoke `e.preventDefault()` to prevent browser's context menu from appearing.

```
$('#my-div').on('contextmenu', function(e) {
  e.preventDefault();
  superCm.createMenu([...], e);
});
```

### Structuring the menu
![Alt text](https://imgur.com/download/qopz3kl "Example Context Menu")

The `options` argument accepts an array of object that can be structured as follows:

```
var options = [
  {
    icon: 'fa fa-plus',   //Icon for the option
    label: 'Add a new item',   //Label to be displayed for the option
    action: function(option, contextMenuIndex, optionIndex) {...},   //The callback once clicked
    submenu: [...],   //An array of object for submenus once hovered
    disabled: false   //Disabled status of the option          
  },
  {
    separator: true   //Menu separator
  }
];
```

### Option properties
#### Icon
The `icon` property can be used to specify an icon for the menu option. This property is injected as a class so you can use icon plugins like FontAwesome.

```
icon: 'fa fa-info'
```

#### Label
Self-explanatory, the `label` property is the text displayed for the option.

```
label: 'Example Option'
```

#### Action
This is the callback that is called upon clicking or pressing enter on the option. The callback has three parameter:

`option`: the option object that is selected. It is recommended that this is used over `superCm.getMenuOptions` to obtain the option object as `superCm.getMenuOptions` will obtain the incorrect option object while searching.

`contextMenuIndex`: a zero based index that specifies the selected option's context menu. Zero is the first context menu that appears upon `superCm.createMenu`.

`optionIndex`: a zero based index that specifies the selected option's index.

```
action: function(option, contextMenuIndex, optionIndex) {
  alert('You have selected option number ' + optionIndex);
}
```

#### Submenu
The `submenu` property can be used to create submenus that appear upon hover. The property accepts array of objects that has the same structure as usual option object. There is no limit for submenus that can be created.

```
submenu: [
  {
    icon: 'fa fa-exclamation',
    label: 'Example Suboption 1',
  },
  {
    icon: 'fa fa-question',
    label: 'Example Suboption 2',
  }
]
```

#### Disabled
This property signifies that the option is disabled and cannot be clicked. The action callback will also be disabled.

```
disabled: true
```

#### Separator
Creates a separator line. Adding this property will disable any other option property.

```
separator: true
```

#### Custom properties
You can also add your own properties to the option object. This allows data to be stored on each option and be obtained later either through the `option` parameter in the action callback, the `this` keyword, or the `superCm.getMenuOptions` function.

```
function process(option) {
  alert('Processing user with ID ' + option.userId + ' and role ' + option.role);
  superCm.destroyMenu();
}

$(document).on('contextmenu', function(e) {
  e.preventDefault();
  superCm.createMenu([
    {
      icon: 'fa fa-user',
      label: 'User 1',
      action: process,
      userId: 'U1234EX',
      role: 'Admin'
    },
    {
      icon: 'fa fa-user',
      label: 'User 2',
      action: process,
      userId: 'U8484PL',
      role: 'Member'
    }
  ], e);
});
```

### Functions

1. `superCm.createMenu(options, event)`

2. `superCm.destroyMenu()`

3. `superCm.updateMenu(allowHorzReposition = true, allowVertReposition = true)`

4. `superCm.getMenuOptions(contextMenuIndex)`

5. `superCm.addMenuOption(contextMenuIndex, option, [index])`

6. `superCm.addMenuOptions(contextMenuIndex, options, [index])`

7. `superCm.deleteMenuOption(contextMenuIndex, index)`

8. `superCm.setMenuOption(contextMenuIndex, index, option)`

9. `superCm.setMenuOptions(contextMenuIndex, options)`

