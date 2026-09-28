#pragma once
#define VKAPI_PTR
#define VKAPI_ATTR
#define VKAPI_CALL

// Stub: HWUI_NO_VULKAN should disable Vulkan paths but headers still reference types.
#include <cstdint>

typedef void* VkInstance;
typedef void* VkDevice;
typedef void* VkPhysicalDevice;
typedef void* VkQueue;
typedef void* VkCommandBuffer;
typedef void* VkImage;
typedef void* VkImageView;
typedef void* VkBuffer;
typedef void* VkSemaphore;
typedef void* VkFence;
typedef void* VkRenderPass;
typedef void* VkFramebuffer;
typedef void* VkSurfaceKHR;
typedef void* VkSwapchainKHR;
typedef void* VkSampler;
typedef void* VkDescriptorPool;
typedef void* VkDescriptorSet;
typedef void* VkDescriptorSetLayout;
typedef void* VkPipelineLayout;
typedef void* VkPipeline;
typedef void* VkShaderModule;
typedef void* VkDeviceMemory;
typedef void* VkEvent;
typedef void* VkQueryPool;
typedef void* VkBufferView;
typedef int VkResult;
typedef int VkFormat;
typedef int VkImageLayout;
typedef int VkImageUsageFlags;
typedef int VkSampleCountFlagBits;
typedef int VkSharingMode;
typedef int VkImageTiling;
typedef int VkColorSpaceKHR;
typedef int VkPresentModeKHR;
typedef unsigned int VkBool32;
typedef unsigned int VkFlags;
typedef unsigned long long VkDeviceSize;
typedef unsigned int VkStructureType;

#define VK_NULL_HANDLE nullptr
enum {
    VK_IMAGE_LAYOUT_UNDEFINED = 0,
    VK_SUCCESS = 0,
    VK_FALSE = 0,
    VK_TRUE = 1,
};

struct VkExtent2D { unsigned int width, height; };
struct VkExtent3D { unsigned int width, height, depth; };
struct VkPhysicalDeviceFeatures { VkBool32 robustBufferAccess; };
struct VkPhysicalDeviceFeatures2 { VkStructureType sType; void* pNext; VkPhysicalDeviceFeatures features; };
struct VkPhysicalDeviceProperties { uint32_t apiVersion; };
struct VkPhysicalDeviceMemoryProperties { uint32_t memoryTypeCount; };
struct VkApplicationInfo { VkStructureType sType; };
struct VkInstanceCreateInfo { VkStructureType sType; };
struct VkDeviceCreateInfo { VkStructureType sType; };
struct VkQueueFamilyProperties { uint32_t queueCount; };
struct VkAllocationCallbacks { void* pUserData; };
struct VkCommandPool { void* p; };
struct VkExtensionProperties { char extensionName[256]; uint32_t specVersion; };
struct VkLayerProperties { char layerName[256]; uint32_t specVersion; uint32_t implVersion; char description[256]; };
struct VkImageFormatProperties2 { VkStructureType sType; void* pNext; };
struct VkPhysicalDeviceImageFormatInfo2 { VkStructureType sType; void* pNext; };

typedef int VkPipelineStageFlags;
typedef int VkAccessFlags;
typedef int VkImageAspectFlags;
typedef int VkMemoryHeapFlags;
typedef int VkMemoryPropertyFlags;
typedef int VkSurfaceTransformFlagBitsKHR;
typedef int VkCompositeAlphaFlagBitsKHR;
typedef int VkExternalMemoryHandleTypeFlagBits;
typedef int VkDescriptorType;
typedef int VkShaderStageFlags;

// Function pointer typedefs (PFN_*)
typedef VkResult (VKAPI_PTR *PFN_vkVoidFunction)(void);
typedef PFN_vkVoidFunction (VKAPI_PTR *PFN_vkGetInstanceProcAddr)(VkInstance, const char*);
typedef PFN_vkVoidFunction (VKAPI_PTR *PFN_vkGetDeviceProcAddr)(VkDevice, const char*);

typedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceVersion)(uint32_t*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceExtensionProperties)(const char*, uint32_t*, VkExtensionProperties*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceLayerProperties)(uint32_t*, VkLayerProperties*);
typedef VkResult (VKAPI_PTR *PFN_vkCreateInstance)(const void*, const VkAllocationCallbacks*, VkInstance*);
typedef void     (VKAPI_PTR *PFN_vkDestroyInstance)(VkInstance, const VkAllocationCallbacks*);

typedef VkResult (VKAPI_PTR *PFN_vkEnumeratePhysicalDevices)(VkInstance, uint32_t*, VkPhysicalDevice*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceProperties)(VkPhysicalDevice, VkPhysicalDeviceProperties*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceQueueFamilyProperties)(VkPhysicalDevice, uint32_t*, VkQueueFamilyProperties*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceFeatures2)(VkPhysicalDevice, VkPhysicalDeviceFeatures2*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceImageFormatProperties2)(VkPhysicalDevice, const VkPhysicalDeviceImageFormatInfo2*, VkImageFormatProperties2*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceMemoryProperties)(VkPhysicalDevice, VkPhysicalDeviceMemoryProperties*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceMemoryProperties2)(VkPhysicalDevice, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceFormatProperties)(VkPhysicalDevice, VkFormat, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceFormatProperties2)(VkPhysicalDevice, VkFormat, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)(VkPhysicalDevice, VkSurfaceKHR, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfaceFormatsKHR)(VkPhysicalDevice, VkSurfaceKHR, uint32_t*, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfacePresentModesKHR)(VkPhysicalDevice, VkSurfaceKHR, uint32_t*, VkPresentModeKHR*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfaceSupportKHR)(VkPhysicalDevice, uint32_t, VkSurfaceKHR, VkBool32*);

typedef VkResult (VKAPI_PTR *PFN_vkCreateDevice)(VkPhysicalDevice, const void*, const VkAllocationCallbacks*, VkDevice*);
typedef void     (VKAPI_PTR *PFN_vkDestroyDevice)(VkDevice, const VkAllocationCallbacks*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateDeviceExtensionProperties)(VkPhysicalDevice, const char*, uint32_t*, VkExtensionProperties*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateDeviceLayerProperties)(VkPhysicalDevice, uint32_t*, VkLayerProperties*);

typedef void     (VKAPI_PTR *PFN_vkGetDeviceQueue)(VkDevice, uint32_t, uint32_t, VkQueue*);
typedef VkResult (VKAPI_PTR *PFN_vkDeviceWaitIdle)(VkDevice);
typedef VkResult (VKAPI_PTR *PFN_vkQueueWaitIdle)(VkQueue);
typedef VkResult (VKAPI_PTR *PFN_vkQueueSubmit)(VkQueue, uint32_t, const void*, VkFence);

// Catch-all for any other unused PFN — typedef as opaque function pointer
typedef PFN_vkVoidFunction PFN_vkAllocateMemory;
typedef PFN_vkVoidFunction PFN_vkFreeMemory;
typedef PFN_vkVoidFunction PFN_vkMapMemory;
typedef PFN_vkVoidFunction PFN_vkUnmapMemory;
typedef PFN_vkVoidFunction PFN_vkBindBufferMemory;
typedef PFN_vkVoidFunction PFN_vkBindImageMemory;
typedef PFN_vkVoidFunction PFN_vkCreateImage;
typedef PFN_vkVoidFunction PFN_vkDestroyImage;
typedef PFN_vkVoidFunction PFN_vkCreateBuffer;
typedef PFN_vkVoidFunction PFN_vkDestroyBuffer;
typedef PFN_vkVoidFunction PFN_vkCreateImageView;
typedef PFN_vkVoidFunction PFN_vkDestroyImageView;
typedef PFN_vkVoidFunction PFN_vkCreateBufferView;
typedef PFN_vkVoidFunction PFN_vkDestroyBufferView;
typedef PFN_vkVoidFunction PFN_vkCreateFramebuffer;
typedef PFN_vkVoidFunction PFN_vkDestroyFramebuffer;
typedef PFN_vkVoidFunction PFN_vkCreateRenderPass;
typedef PFN_vkVoidFunction PFN_vkDestroyRenderPass;
typedef PFN_vkVoidFunction PFN_vkCreateCommandPool;
typedef PFN_vkVoidFunction PFN_vkDestroyCommandPool;
typedef PFN_vkVoidFunction PFN_vkAllocateCommandBuffers;
typedef PFN_vkVoidFunction PFN_vkFreeCommandBuffers;
typedef PFN_vkVoidFunction PFN_vkResetCommandPool;
typedef PFN_vkVoidFunction PFN_vkBeginCommandBuffer;
typedef PFN_vkVoidFunction PFN_vkEndCommandBuffer;
typedef PFN_vkVoidFunction PFN_vkResetCommandBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdPipelineBarrier;
typedef PFN_vkVoidFunction PFN_vkCmdCopyBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdCopyImage;
typedef PFN_vkVoidFunction PFN_vkCmdCopyBufferToImage;
typedef PFN_vkVoidFunction PFN_vkCmdCopyImageToBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdBeginRenderPass;
typedef PFN_vkVoidFunction PFN_vkCmdEndRenderPass;
typedef PFN_vkVoidFunction PFN_vkCmdNextSubpass;
typedef PFN_vkVoidFunction PFN_vkCmdBindPipeline;
typedef PFN_vkVoidFunction PFN_vkCmdBindDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkCmdBindVertexBuffers;
typedef PFN_vkVoidFunction PFN_vkCmdBindIndexBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdDraw;
typedef PFN_vkVoidFunction PFN_vkCmdDrawIndexed;
typedef PFN_vkVoidFunction PFN_vkCmdSetViewport;
typedef PFN_vkVoidFunction PFN_vkCmdSetScissor;
typedef PFN_vkVoidFunction PFN_vkCmdClearColorImage;
typedef PFN_vkVoidFunction PFN_vkCmdClearDepthStencilImage;
typedef PFN_vkVoidFunction PFN_vkCmdClearAttachments;
typedef PFN_vkVoidFunction PFN_vkCmdResolveImage;
typedef PFN_vkVoidFunction PFN_vkCreateSemaphore;
typedef PFN_vkVoidFunction PFN_vkDestroySemaphore;
typedef PFN_vkVoidFunction PFN_vkCreateFence;
typedef PFN_vkVoidFunction PFN_vkDestroyFence;
typedef PFN_vkVoidFunction PFN_vkResetFences;
typedef PFN_vkVoidFunction PFN_vkGetFenceStatus;
typedef PFN_vkVoidFunction PFN_vkWaitForFences;
typedef PFN_vkVoidFunction PFN_vkCreateSampler;
typedef PFN_vkVoidFunction PFN_vkDestroySampler;
typedef PFN_vkVoidFunction PFN_vkCreateDescriptorPool;
typedef PFN_vkVoidFunction PFN_vkDestroyDescriptorPool;
typedef PFN_vkVoidFunction PFN_vkAllocateDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkFreeDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkUpdateDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkCreateDescriptorSetLayout;
typedef PFN_vkVoidFunction PFN_vkDestroyDescriptorSetLayout;
typedef PFN_vkVoidFunction PFN_vkCreatePipelineLayout;
typedef PFN_vkVoidFunction PFN_vkDestroyPipelineLayout;
typedef PFN_vkVoidFunction PFN_vkCreateGraphicsPipelines;
typedef PFN_vkVoidFunction PFN_vkCreateComputePipelines;
typedef PFN_vkVoidFunction PFN_vkDestroyPipeline;
typedef PFN_vkVoidFunction PFN_vkCreateShaderModule;
typedef PFN_vkVoidFunction PFN_vkDestroyShaderModule;
typedef PFN_vkVoidFunction PFN_vkGetBufferMemoryRequirements;
typedef PFN_vkVoidFunction PFN_vkGetImageMemoryRequirements;
typedef PFN_vkVoidFunction PFN_vkGetImageMemoryRequirements2;
typedef PFN_vkVoidFunction PFN_vkGetBufferMemoryRequirements2;
typedef PFN_vkVoidFunction PFN_vkInvalidateMappedMemoryRanges;
typedef PFN_vkVoidFunction PFN_vkFlushMappedMemoryRanges;
typedef PFN_vkVoidFunction PFN_vkBindImageMemory2;
typedef PFN_vkVoidFunction PFN_vkBindBufferMemory2;


// Round 13: more PFN_vk* typedefs needed by VulkanManager.h
typedef PFN_vkVoidFunction PFN_vkImportSemaphoreFdKHR;
typedef PFN_vkVoidFunction PFN_vkGetSemaphoreFdKHR;
typedef PFN_vkVoidFunction PFN_vkImportFenceFdKHR;
typedef PFN_vkVoidFunction PFN_vkGetFenceFdKHR;
typedef PFN_vkVoidFunction PFN_vkCreateSwapchainKHR;
typedef PFN_vkVoidFunction PFN_vkDestroySwapchainKHR;
typedef PFN_vkVoidFunction PFN_vkGetSwapchainImagesKHR;
typedef PFN_vkVoidFunction PFN_vkAcquireNextImageKHR;
typedef PFN_vkVoidFunction PFN_vkQueuePresentKHR;
typedef PFN_vkVoidFunction PFN_vkCreateAndroidSurfaceKHR;
typedef PFN_vkVoidFunction PFN_vkDestroySurfaceKHR;
typedef PFN_vkVoidFunction PFN_vkCmdSetEventKHR;
typedef PFN_vkVoidFunction PFN_vkResetEventKHR;
typedef PFN_vkVoidFunction PFN_vkWaitEventsKHR;

#ifndef VK_MAKE_VERSION
#define VK_MAKE_VERSION(major, minor, patch) \
    (((major) << 22) | ((minor) << 12) | (patch))
#endif

#ifndef VK_API_VERSION_1_1
#define VK_API_VERSION_1_1 VK_MAKE_VERSION(1, 1, 0)
#endif
