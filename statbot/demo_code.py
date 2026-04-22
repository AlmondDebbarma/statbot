
def binary_search(arr, target):
    \"\"\"
    A flawed binary search implementation for testing.
    Can you find the bug?
    \"\"\"
    low = 0
    high = len(arr) - 1

    while low <= high:
        mid = (low + high) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            # BUG: Should be high = mid - 1
            high = mid
            
    return -1

if __name__ == "__main__":
    nums = [1, 3, 5, 7, 9, 11]
    print(binary_search(nums, 3)) # Should return 1
    print(binary_search(nums, 8)) # Will loop infinitely because of the bug!
