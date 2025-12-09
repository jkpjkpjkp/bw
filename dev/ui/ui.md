write the skeleton of a Tinder clone, using react.

the implementation is minimal, without user control and do not need communicating with a remote server. 

supported features:

- these are all ancient people, so when user specify a `desired age`, it do not filter anyone, instead each person displays a `year`, indicating in what year are they that age, and a photo of that age is displayed. 
- everyone is identified by first name only, their last names are too well-known
- swipe left/right to dislike/like. when dislike, the deck of persons shows the next person. when like, the book reader is shown, starting from the chapter whose age range contains current user's preference and has a thinnest range span. during reading can always swipe left to dislike. single click is prev/next page, and swipe right is `add to library`. 