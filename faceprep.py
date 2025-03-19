a=int(input("enter the number"))
count=0
for i in range(1,a+1):
    if a%i==0:
        count+=1
if count==2:
    print("Given number is prime")
else:
    print("given number is not a prime number")
