Test via cdn:https://mydynamicmediacdnendpoint.azureedge.net/api/dynamicmediahandler?filename=product1.jpg&width=700&height=500&format=png

Test via Az fun:https://mycdn.azurewebsites.net/api/dynamicmediahandler?filename=product3.jpg&code=abc 
or pass code in header
 https://myfunctionappdynamic.azurewebsites.net/api/dynamicmediahandler?filename=product1.jpg&width=800&height=300&format=png" -H "x-functions-key: abc

 When I created this mycdnendpoint I did 2 things


 
 1)Query string caching behavior :Cache Every Unique URL
 ![image](https://github.com/user-attachments/assets/a0ec6db8-795a-4514-9e04-54217647cd94)




 2)Added Rule:
 ![image](https://github.com/user-attachments/assets/b6550715-bfe4-485a-bf3d-98cddcf03531)


 
